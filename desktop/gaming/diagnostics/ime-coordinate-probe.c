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
    if (argc != 2 || (strcmp(argv[1], "--composition") &&
                      strcmp(argv[1], "--candidate"))) return 2;
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
    ShowWindow(window, SW_SHOWNOACTIVATE);
    MSG message;
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    return 0;
}
