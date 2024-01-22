#include <wayland-client.h>

// struct that holds compositor state
struct nichtwm {
    struct wl_display *wl_display;
    struct wl_event_loop *wl_event_loop;

    struct wlr_backend *backend; // include backend member
};

// wayland display event loop
// (app signals, notification of data file descriptors, etc)
int main(int argc, char **argv) {
    struct nichtwm server;

    // create wayland display
    server.wl_display = wl_display_create();
    assert(server.wl_display);

    // get wayland event loop
    server.wl_event_loop = wl_display_get_event_loop(server.wl_display);
    assert(server.wl_event_loop);

    // wlroots helper function
    // (auto. chooses best backend based on users environment)
    server.backend = wlr_backend_autocreate(server.wl_display);
    assert(server.backend);

    // start backend and enter Wayland event loop
    if (!wlr_backend_start(server.backend)) {
        fprintf(stderr, "Failed to start backend\n");
        wl_display_destroy(server.wl_display);
        return 1;
    };
     
    return 0;
};

// wlroots backend
// abstracts low level in/output implementations
// (mice, keyboards, monitors, etc)

/*
Available backends:
    - drm: render to displays
    - libinput: enumerates/controls physical input
    - wayland: outputs as windows on another wayland compositor.
               allows to nest compositors (debugging)
    - x11: same as wayland but using x11.
    - multi: combine multiple backends and their in/outputs.
*/

