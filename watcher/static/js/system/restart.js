/* global url_base, notify_error */
/* Automatically restarts server when loaded.

If url has query string ?e=false, does not instruct server to restart, only checks for server to come back online

*/

window.addEventListener("DOMContentLoaded", function(){

    document.title = "Watcher - Restarting Server";
    var qstring = new URLSearchParams(window.location.search);

    var $thinker = document.getElementById("thinker");
    $thinker.style.maxHeight = '100%';

    if(qstring.get("e") !== "false"){
        $.post(url_base + "/ajax/server_status", {
            mode: 'restart'
        })
        .fail(notify_error);
    }

    /*
    This repeats every 3 seconds to check. Times out after 10 attempts and
        shows span.error message.
    */
    var try_count = 0;
    var check = setInterval(function(){
        if(try_count < 10){
            try_count += 1;
            $.post(url_base + "/ajax/server_status", {
                mode: "online",
            })
            .done(function(r){
                if(r !== "states.STOPPING"){
                    window.location = url_base+"/library/status/";
                }
            });
        } else {
            clearInterval(check);
            document.title = "Watcher - Error";
            $.notify({message: _("Watcher is taking too long to restart. Please check your logs and restart manually.")}, {type: "warning", delay: 0})
            $thinker.style.maxHeight = '0%';
        }
    }, 3000);
});
