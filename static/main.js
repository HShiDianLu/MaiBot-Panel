$(".loader").css("opacity", "1");
$("#navbar").css("opacity", "1");

function websiteIn() {
    $(".loader").css("opacity", "0");
    $("#loader-background").css("opacity", "0");
    setTimeout(function () {
        $(".loader").css("display", "none");
        $("#loader-background").css("display", "none");
    }, 300)
    contentOut();
}

function appear(i) {
    let blocks = document.getElementsByClassName("box");
    blocks[i].style.opacity = "1";
    blocks[i].style.top = "0";
}

function contentOut() {
    let basic = 100;
    let blocks = document.getElementsByClassName("box");
    for (let i = 0; i < blocks.length; i++) {
        setTimeout("appear(" + i + ")", basic * i);
    }
}

$(window).on('load', function () {
    websiteIn();
    //clearTimeout(loadTimeout);
});

setInterval(function () {
    $("#log-content").css("width", $(".log-box").width() + "px");
    $("#log-content").css("height", $(".log-box").height() - 105 + "px");
}, 100)
$("#log-content").scrollTop($("#log-content")[0].scrollHeight);

let t = setInterval(function () {
    $("#log-content").scrollTop($("#log-content")[0].scrollHeight);
}, 10);
let s = false;

function switchScroll() {
    if (s) {
        t = setInterval(function () {
            $("#log-content").scrollTop($("#log-content")[0].scrollHeight);
        }, 10);
    } else {
        clearInterval(t);
    }
    s = !s;
}

var socket = io();

socket.on('dataRefresh', function (result) {
    for (let k in result.data) {
        $("#" + k).text(result.data[k]);
    }
});

socket.on('newLog', function (result) {
    console.log(result);
    for (let i = 0; i < result.data.length; i++) {
        let logItem = result.data[i];
        let logElement = $("<p class='log " + logItem.level + "'>" + logItem.timestamp + " | " + logItem.logger_name + ": " + logItem.event + "</p>");
        $("#log-content").append(logElement);
    }
});

socket.on('newLogFile', function (result) {
    console.log(result);
    $("#logName").text(result.file);
    $("#log-content").empty();
    for (let i = 0; i < result.data.length; i++) {
        let logItem = result.data[i];
        let logElement = $("<p class='log " + logItem.level + "'>" + logItem.timestamp + " | " + logItem.logger_name + ": " + logItem.event + "</p>");
        $("#log-content").append(logElement);
    }
});

socket.on('apiRefresh', function (result) {
    console.log(result);
    let service = result['data']['service'];
    let api = result['data']['api']
    for (let k in service) {
        $("#s-" + api[k]['name']).removeClass("green");
        $("#s-" + api[k]['name']).removeClass("red");
        if (api[k]['status']) {
            $("#s-" + api[k]['name']).addClass("green");
        } else {
            $("#s-" + api[k]['name']).addClass("red");
        }
    }
    for (let k in api) {
        $("#api-" + api[k]['name']).removeClass("green");
        $("#api-" + api[k]['name']).removeClass("red");
        if (api[k]['status']) {
            $("#api-" + api[k]['name']).addClass("green");
        } else {
            $("#api-" + api[k]['name']).addClass("red");
        }
        $("#p-" + api[k]['name']).text(api[k]['ping'] + "ms");
    }
});