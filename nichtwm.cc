#include <wayland-client.h>

// struct that holds compositor state
struct nichtwm_server {
    struct wl_display *wl_display;
    struct wl_event_loop *wl_event_loop;

    // wlroots backend
    struct wlr_backend *backend; // include backend member
    // listens for new outputs
    struct wl_listener new_output;

    // abstracts low level in/output implementations
    // (mice, keyboards, monitors, etc)
    struct wl_list outputs; // nichtwm_output::link
};

struct nichtwm_output {
    struct wlr_output *wlr_output;
    struct nichtwm_server *server;
    struct timespec last_frame;

    struct wl_list link;
};

static void new_output_notify(struct wl_listener *listener, void *data) {
    struct nichtwm_server *server = wl_container_of(listener, server, new_output);
    
    struct wlr_output *wlr_output = data;

    if (!wl_list_empty(&wlr_output->modes)) {
        struct wlr_output_mode *mode = wl_container_of(wlr_output->modes.prev, mode, link);
        wlr_output_set_mode(wlr_output, mode);
    }
    
    // Call nwm output function
    struct nichtwm_output *output = calloc(1, sizeof(struct nichtwm_output));
    clock_gettime(CLOCK_MONOTONIC, &output->last_frame);
    output->server = server;
    output->wlr_output = wlr_output;
    wl_list_insert(&server->outputs, &output->link);
}


//  structure we use to store any state we have for this output that is specific to our compositor’s needs

// wayland display event loop
// (app signals, notification of data file descriptors, etc)
int main(int argc, char **argv) {
    struct nichtwm_server server;

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

    // specify function to be notified, via wl_signal_add
    wl_list_init(&server.outputs);
    server.new_output.notify = new_output_notify;
    wl_signal_add(&server.backend->events.new_output, &server.new_output);

    // start backend and enter Wayland event loop
    if (!wlr_backend_start(server.backend)) {
        fprintf(stderr, "Failed to start backend\n");
        wl_display_destroy(server.wl_display);
        return 1;
    };
     
    return 0;
};

/*
Available backends:
    - drm: render to displays
    - libinput: enumerates/controls physical input
    - wayland: outputs as windows on another wayland compositor.
               allows to nest compositors (debugging)
    - x11: same as wayland but using x11.
    - multi: combine multiple backends and their in/outputs.
*/