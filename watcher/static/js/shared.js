window.addEventListener("DOMContentLoaded", function(){
    url_base = document.querySelector("meta[name='url_base']").content;
    show_notifs = JSON.parse(document.querySelector("meta[name='enable_notifs']").content || "true");
    language = document.querySelector("meta[name='language']").content || "en";

    if(show_notifs){
        notifs = JSON.parse(document.querySelector("script#notifications_json").innerHTML);

        show_notifications(notifs);
    }
});

function show_notifications(notifs){
    /* Shows notifications in DOM
    notifs (list): tuples of notification options, settings
    */
    each(notifs, function(notif, index){
        notif[1]["onClose"] = remove_notif;
        var n = $.notify(notif[0], notif[1]);
        n["$ele"].attr("data-index", notif[1]["index"]);
    });
}

function notify_error(data){
    var err = data.status + " " + data.statusText;
    $.notify({message: err}, {type: "danger", delay: 0});
}

function logout(event){
    event.preventDefault();

    $.post(url_base + "/auth/logout", {})
        .done(function(r){
            window.location = r;
        })
        .fail(notify_error);
}

$.notifyDefaults({
    type: "success",
    allow_dismiss: true,
    delay: 3000,
    placement: {from: "bottom"},
    animate: {
        enter: "animated fadeInDown",
        exit: "animated fadeOutDown"
    }
});

function remove_notif(){
    var index = this[0].dataset.index;
    if(index === undefined){
        return false;
    }
    $.post(window.url_base + "/ajax/notification_remove", {
        "index": index
    });
}


function format_template(t, d){
    // t: template node
    // d: dict to substitue
    // Returns HTML node
    for (var p in d) {
        var val = d[p];
        if(val === null || val === undefined) val = "";
        t = t.replace(new RegExp("{" + p + "}", "g"), val);
    }
    return $.parseHTML(t.trim())[0];
}

function each(arr, fn){
    // Executes fn(array_item, array_index) for each item in arr
    // Break loop by returning false in fn
    for (var i = 0; i < arr.length; i++) {
        if(fn(arr[i], i) === false){
            break;
        }
    }
}

function _start_update(event){
    // Method called to start update from notification.
    event.preventDefault();
    $.post(url_base + "/ajax/update_server", {"mode": "set_true"})
        .done(function(){
            window.location = url_base + "/system/update";
        })
        .fail(notify_error);
}

function alt_execute_task(event, elem, name){
    event.preventDefault();

    if(elem.classList.contains("disabled")){
        return;
    }
    elem.classList.add("disabled");

    if(elem.classList.contains("mdi-play-circle")){
        elem.classList.remove("mdi-play-circle");
        elem.classList.add("mdi-circle");
        elem.classList.add("animated");
    }

    return $.post(url_base + "/ajax/manual_task_execute", {name: name})
        .done(function(response){
            if(response["response"] === true){
                $.notify({message: response["message"]});
                $.each(response["notifications"], function(i, notif){
                    notif[1]["onClose"] = remove_notif;
                    var n = $.notify(notif[0], notif[1]);
                    n["$ele"].attr("data-index", notif[1]["index"]);
                });
            } else {
                $.notify({message: response["error"]}, {type: "danger", delay: 0});
            }
        })
        .fail(notify_error)
        .always(function(){
            if(elem.classList.contains("mdi-circle")){
                elem.classList.remove("mdi-circle");
                elem.classList.remove("animated");
                elem.classList.add("mdi-play-circle");
            }
            elem.classList.remove("disabled");
        });
}

function _(s){
    /* Localization method
    s (str): string to look for in translation file

    returns string
    */
    if(language === "en"){
        return s;
    } else {
        return languages[language][s] || s;
    }


}
