/* Original Utopia code: normal Win32 repaint, no injection/input/geometry edits.
 * Build as Windows PE, NOT a Unix Winelib .exe.so; see hearthstone-cn.md.
 */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <stdio.h>
#include <string.h>

static HWND target;
static BOOL CALLBACK find_client(HWND hwnd, LPARAM unused)
{
    WCHAR title[32], image[4096], *base, *p;
    DWORD pid, length = 4096;
    HANDLE process;
    if (!IsWindowVisible(hwnd) || !GetWindowTextW(hwnd, title, 32) ||
        lstrcmpW(title, L"战网")) return TRUE;
    GetWindowThreadProcessId(hwnd, &pid);
    process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!process) return TRUE;
    if (!QueryFullProcessImageNameW(process, 0, image, &length)) {
        CloseHandle(process); return TRUE;
    }
    CloseHandle(process);
    base = image;
    for (p = image; *p; ++p) if (*p == '\\') base = p + 1;
    if (lstrcmpiW(base, L"Battle.net.exe")) return TRUE;
    target = hwnd;
    return FALSE;
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--self-test")) {
        puts("Battle.net PE repaint helper ready");
        return 0;
    }
    if (argc != 2 || (strcmp(argv[1], "--once") && strcmp(argv[1], "--limits"))) return 2;
    EnumWindows(find_client, 0);
    if (!target) return 1;
    if (!strcmp(argv[1], "--limits")) {
        MINMAXINFO limits = {0};
        DWORD_PTR result;
        SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        if (!SendMessageTimeoutW(target, WM_GETMINMAXINFO, 0, (LPARAM)&limits,
                                 SMTO_ABORTIFHUNG, 1000, &result)) return 1;
        printf("{\"min_width\":%ld,\"min_height\":%ld,\"dpi\":%u}\n",
               limits.ptMinTrackSize.x, limits.ptMinTrackSize.y, GetDpiForWindow(target));
        return 0;
    }
    return RedrawWindow(target, NULL, NULL,
                       RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN | RDW_UPDATENOW) ? 0 : 1;
}
