/* Original Utopia diagnostic: own window only; no game hooks or text logging.
 * Build as Windows PE. This reproducer is not a deployed workaround.
 */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <imm.h>
#include <stdio.h>
#include <string.h>

static int candidate_only;
static POINT spot;

static int module_fingerprint(void)
{
    HMODULE module = GetModuleHandleW(L"imm32.dll");
    FARPROC address = module ? GetProcAddress(module, "ImmSetCandidateWindow") : NULL;
    if (!address) return 1;
    /* Only this probe's own code is read, never a game's memory or input. */
    const unsigned char *code = (const unsigned char *)address;
    unsigned long long fingerprint = 0xcbf29ce484222325ULL;
    for (unsigned i = 0; i < 64; i++) {
        fingerprint ^= code[i];
        fingerprint *= 0x100000001b3ULL;
    }
    printf("own_candidate_code_fingerprint=%016llx\n", fingerprint);
    return 0;
}

static int contract_test(HWND window)
{
    HIMC context = ImmGetContext(window);
    COMPOSITIONFORM expected = {0}, observed = {0};
    CANDIDATEFORM candidate = {0}, stored = {0};
    int failed = 0;
    if (!context) { puts("contract_context_unavailable"); return 1; }
    expected.dwStyle = CFS_POINT;
    expected.ptCurrentPos.x = 17;
    expected.ptCurrentPos.y = 23;
    if (!ImmSetCompositionWindow(context, &expected)) failed++;
    for (unsigned i = 0; i < 4; i++) {
        candidate.dwIndex = (i == 2) ? 1 : 0;
        candidate.dwStyle = (i == 1) ? CFS_EXCLUDE :
                            (i == 3) ? CFS_DEFAULT : CFS_CANDIDATEPOS;
        candidate.ptCurrentPos.x = 120;
        candidate.ptCurrentPos.y = 320;
        SetRect(&candidate.rcArea, 120, 300, 360, 340);
        if (!ImmSetCandidateWindow(context, &candidate)) failed++;
        if (!ImmGetCandidateWindow(context, candidate.dwIndex, &stored) ||
            stored.dwIndex != candidate.dwIndex || stored.dwStyle != candidate.dwStyle ||
            stored.ptCurrentPos.x != candidate.ptCurrentPos.x ||
            stored.ptCurrentPos.y != candidate.ptCurrentPos.y ||
            !EqualRect(&stored.rcArea, &candidate.rcArea)) failed++;
        if (!ImmGetCompositionWindow(context, &observed) ||
            observed.dwStyle != expected.dwStyle ||
            observed.ptCurrentPos.x != expected.ptCurrentPos.x ||
            observed.ptCurrentPos.y != expected.ptCurrentPos.y ||
            !EqualRect(&observed.rcArea, &expected.rcArea)) failed++;
    }
    if (ImmSetCandidateWindow(context, NULL)) failed++;
    candidate.dwIndex = 32;
    if (ImmSetCandidateWindow(context, &candidate)) failed++;
    ImmReleaseContext(window, context);
    printf("candidate_form_contract_failures=%d\n", failed);
    return failed ? 1 : 0;
}

static void update_anchor(HWND window)
{
    RECT area;
    HIMC context = ImmGetContext(window);
    if (!context) { puts("own_context_unavailable"); fflush(stdout); return; }
    GetClientRect(window, &area);
    spot.x = area.right / 5;
    spot.y = area.bottom * 3 / 4;
    if (candidate_only) {
        CANDIDATEFORM form = {0};
        form.dwStyle = CFS_CANDIDATEPOS;
        form.ptCurrentPos = spot;
        printf("candidate_api_ok=%d", ImmSetCandidateWindow(context, &form));
    } else {
        COMPOSITIONFORM form = {0};
        form.dwStyle = CFS_POINT;
        form.ptCurrentPos = spot;
        printf("composition_api_ok=%d", ImmSetCompositionWindow(context, &form));
    }
    POINT screen = spot;
    ClientToScreen(window, &screen);
    printf(" client=%ld,%ld screen=%ld,%ld dpi=%u\n",
           spot.x, spot.y, screen.x, screen.y, GetDpiForWindow(window));
    fflush(stdout);
    ImmReleaseContext(window, context);
    InvalidateRect(window, NULL, TRUE);
}

static LRESULT CALLBACK procedure(HWND window, UINT message, WPARAM w, LPARAM l)
{
    switch (message) {
    case WM_SETFOCUS:
    case WM_IME_STARTCOMPOSITION:
        update_anchor(window);
        return 0;
    case WM_IME_COMPOSITION:
        /* No composition/result string is read or recorded. */
        update_anchor(window);
        return 0;
    case WM_CHAR:
        return 0;
    case WM_IME_SETCONTEXT:
        return DefWindowProcW(window, message, w, 0);
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(window, &ps);
        RECT client;
        GetClientRect(window, &client);
        SetBkMode(dc, TRANSPARENT);
        HFONT font = CreateFontW(32, 0, 0, 0, FW_NORMAL, FALSE, FALSE,
                               FALSE, DEFAULT_CHARSET, 0, 0, 0, 0,
                               L"Microsoft YaHei");
        HGDIOBJ old = SelectObject(dc, font);
        RECT text = {40, 40, client.right - 40, 250};
        DrawTextW(dc, candidate_only ?
            L"位置对照 B：仅报告候选框位置\n点击此窗口，切换中文后输入 nihao。\n只观察候选框位置，不会保存或发送输入。\n完成后按 Esc 关闭。" :
            L"位置对照 A：报告预编辑光标位置\n点击此窗口，切换中文后输入 nihao。\n只观察候选框位置，不会保存或发送输入。\n完成后按 Esc 关闭。",
            -1, &text, DT_LEFT | DT_WORDBREAK);
        RECT marker = {client.right / 5, client.bottom * 3 / 4,
                       client.right / 5 + 240, client.bottom * 3 / 4 + 48};
        FrameRect(dc, &marker, GetStockObject(BLACK_BRUSH));
        DrawTextW(dc, L"候选框应靠近这里", -1, &marker, DT_LEFT);
        SelectObject(dc, old);
        DeleteObject(font);
        EndPaint(window, &ps);
        return 0;
    }
    case WM_KEYDOWN:
        if (w == VK_ESCAPE) DestroyWindow(window);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(window, message, w, l);
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--self-test")) {
        puts("coordinate-only PE probe ready");
        return 0;
    }
    if (argc == 2 && !strcmp(argv[1], "--module-check")) return module_fingerprint();
    if (argc != 2 || (strcmp(argv[1], "--composition") &&
                      strcmp(argv[1], "--candidate") &&
                      strcmp(argv[1], "--contract-test"))) return 2;
    int contracts = !strcmp(argv[1], "--contract-test");
    if (module_fingerprint()) return 5;
    candidate_only = !strcmp(argv[1], "--candidate");
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    HINSTANCE instance = GetModuleHandleW(NULL);
    WNDCLASSW klass = {0};
    klass.lpfnWndProc = procedure;
    klass.hInstance = instance;
    klass.hCursor = LoadCursorW(NULL, IDC_ARROW);
    klass.hbrBackground = GetStockObject(WHITE_BRUSH);
    klass.lpszClassName = L"UtopiaIMECoordinateProbe";
    if (!RegisterClassW(&klass)) return 3;
    HWND window = CreateWindowW(klass.lpszClassName,
            candidate_only ? L"Utopia IME probe B" : L"Utopia IME probe A",
            WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT,
            1400, 900, NULL, NULL, instance, NULL);
    if (!window) return 4;
    if (contracts) {
        int status = contract_test(window);
        DestroyWindow(window);
        return status;
    }
    ShowWindow(window, SW_SHOWNOACTIVATE);
    MSG message;
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    return 0;
}
