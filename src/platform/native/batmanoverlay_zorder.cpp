/*
 * Native C++ Z-Order Watchdog & CBT Hook DLL for BatmanOverlay.
 *
 * Provides high-frequency, GIL-free HWND_TOPMOST window management
 * and CBT hook window-activation interception.
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <atomic>

#define EXPORT extern "C" __declspec(dllexport)

// Shared State
static std::atomic<bool> g_WatchdogRunning(false);
static std::atomic<HWND> g_TargetHWND(NULL);
static HANDLE g_WatchdogThreadHandle = NULL;
static HHOOK g_CBTHookHandle = NULL;

// CBT Hook Procedure to intercept window activation/creation
LRESULT CALLBACK CBTHookProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode >= 0) {
        if (nCode == HCBT_ACTIVATE || nCode == HCBT_CREATEWND) {
            HWND target = g_TargetHWND.load();
            if (target != NULL && IsWindow(target)) {
                SetWindowPos(
                    target,
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS
                );
            }
        }
    }
    return CallNextHookEx(g_CBTHookHandle, nCode, wParam, lParam);
}

// Watchdog Thread Procedure
DWORD WINAPI WatchdogThreadProc(LPVOID lpParam) {
    DWORD intervalMs = PtrToUlong(lpParam);
    if (intervalMs < 10) intervalMs = 16; // Default ~60 Hz

    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_HIGHEST);

    while (g_WatchdogRunning.load()) {
        HWND target = g_TargetHWND.load();
        if (target != NULL && IsWindow(target)) {
            SetWindowPos(
                target,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            );
        }
        Sleep(intervalMs);
    }
    return 0;
}

// --- Exported C Interface ---

EXPORT BOOL StartZOrderWatchdog(HWND hwnd, DWORD interval_ms) {
    if (hwnd == NULL || !IsWindow(hwnd)) {
        return FALSE;
    }

    if (g_WatchdogRunning.load()) {
        g_TargetHWND.store(hwnd);
        return TRUE;
    }

    g_TargetHWND.store(hwnd);
    g_WatchdogRunning.store(true);

    g_WatchdogThreadHandle = CreateThread(
        NULL,
        0,
        WatchdogThreadProc,
        UlongToPtr(interval_ms),
        0,
        NULL
    );

    if (g_WatchdogThreadHandle == NULL) {
        g_WatchdogRunning.store(false);
        return FALSE;
    }

    return TRUE;
}

EXPORT BOOL StopZOrderWatchdog() {
    if (!g_WatchdogRunning.load()) {
        return TRUE;
    }

    g_WatchdogRunning.store(false);

    if (g_WatchdogThreadHandle != NULL) {
        WaitForSingleObject(g_WatchdogThreadHandle, 1000);
        CloseHandle(g_WatchdogThreadHandle);
        g_WatchdogThreadHandle = NULL;
    }

    g_TargetHWND.store(NULL);
    return TRUE;
}

EXPORT BOOL InstallCBTHook(HWND hwnd) {
    if (hwnd == NULL || !IsWindow(hwnd)) {
        return FALSE;
    }

    g_TargetHWND.store(hwnd);

    if (g_CBTHookHandle != NULL) {
        return TRUE;
    }

    g_CBTHookHandle = SetWindowsHookEx(
        WH_CBT,
        CBTHookProc,
        GetModuleHandle(L"batmanoverlay_zorder.dll"),
        0
    );

    return (g_CBTHookHandle != NULL);
}

EXPORT BOOL RemoveCBTHook() {
    if (g_CBTHookHandle == NULL) {
        return TRUE;
    }

    BOOL res = UnhookWindowsHookEx(g_CBTHookHandle);
    g_CBTHookHandle = NULL;
    return res;
}

EXPORT BOOL IsWatchdogActive() {
    return g_WatchdogRunning.load();
}

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    switch (fdwReason) {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls(hinstDLL);
        break;
    case DLL_PROCESS_DETACH:
        StopZOrderWatchdog();
        RemoveCBTHook();
        break;
    }
    return TRUE;
}
