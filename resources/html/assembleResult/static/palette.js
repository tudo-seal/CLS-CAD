function getDateString() {
    const today = new Date();
    const date = `${today.getDate()}/${today.getMonth() + 1}/${today.getFullYear()}`;
    const time = `${today.getHours()}:${today.getMinutes()}:${today.getSeconds()}`;
    return `Date: ${date}, Time: ${time}`;
}

function sendInfoToFusion() {
    $.get("http://127.0.0.1:8000/results/" + document.getElementById("results-select").value, function (data) {
        console.log(data[document.getElementById("result-select").value])
        // Send the data to Fusion as a JSON string. The return value is a Promise.
        adsk.fusionSendData("assembleMessage", JSON.stringify(data[document.getElementById("result-select").value])).then((result) =>
            document.getElementById("returnValue").innerHTML = `${result}`
        );
    }, "json");

    const args = {
        arg1: document.getElementById("results-select").value,
        arg2: document.getElementById("result-select").value
    };


}

function updateMessage(messageString) {
    // Message is sent from the add-in as a JSON string.
    const messageData = JSON.parse(messageString);

    // Update a paragraph with the data passed in.
    document.getElementById("fusionMessage").innerHTML =
        `<b>Your text</b>: ${messageData.myText} <br/>` +
        `<b>Your expression</b>: ${messageData.myExpression} <br/>` +
        `<b>Your value</b>: ${messageData.myValue}`;
}

window.fusionJavaScriptHandler = {
    handle: function (action, data) {
        try {
            if (action === "updateMessage") {
                updateMessage(data);
            } else if (action === "debugger") {
                debugger;
            } else {
                return `Unexpected command type: ${action}`;
            }
        } catch (e) {
            console.log(e);
            console.log(`Exception caught with command: ${action}, data: ${data}`);
        }
        return "OK";
    },
};
