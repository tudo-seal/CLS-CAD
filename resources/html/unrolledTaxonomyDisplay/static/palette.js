function getDateString() {
    const today = new Date();
    const date = `${today.getDate()}/${today.getMonth() + 1}/${today.getFullYear()}`;
    const time = `${today.getHours()}:${today.getMinutes()}:${today.getSeconds()}`;
    return `Date: ${date}, Time: ${time}`;
}

function sendInfoToFusion() {
    const args = {
        arg1: document.getElementById("sampleData").value,
        arg2: getDateString()
    };

    // Send the data to Fusion as a JSON string. The return value is a Promise.
    adsk.fusionSendData("messageFromPalette", JSON.stringify(args)).then((result) =>
        document.getElementById("returnValue").innerHTML = `${result}`
    );

}

function sendReadyToFusion() {
    // Send the data to Fusion as a JSON string. The return value is a Promise.
    adsk.fusionSendData("readyNotification", "{}").then((result) =>
        console.log(result)
    );
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

var taxonomyID;
var taxonomyOriginalData;
var taxonomyData;

var populated = false;

function sendUpdatedData() {
    var returnData = taxonomyData;
    returnDataString = JSON.stringify(returnData)
    if (returnDataString !== taxonomyOriginalData) {
        adsk.fusionSendData("updateDataNotification", returnDataString).then((result) =>
            console.log(result)
        );
    }

}

function dfsTreeBuild(type, treeNode) {
    (taxonomyData[type] ?? []).forEach(subtype => {
        $('#data').jstree(true).create_node(treeNode, { "text": subtype }, "last", function (new_node) {
            dfsTreeBuild(subtype, new_node);
        });
    });
}

function setTaxonomyData(taxonomyString) {
    taxonomyData = JSON.parse(taxonomyString);
    taxonomyOriginalData = taxonomyString;
    $('#data').jstree(true).create_node("#", { "id": "any", "parent": "#", "text": Object.keys(taxonomyData)[0] })

    dfsTreeBuild(Object.keys(taxonomyData)[0], "any");
    populated = true;

}

window.fusionJavaScriptHandler = {
    handle: function (action, data) {
        try {
            console.log(action)
            if (action === "updateMessage") {
                updateMessage(data);
            } else if (action === "taxonomyDataMessage") {
                console.log("TaxonomyData arrived.")
                setTaxonomyData(data)
            }
            else if (action === "taxonomyIDMessage") {
                console.log("TaxonomyID arrived.")
                document.title = data;
                taxonomyID = data;
            }
            else if (action === "returnTaxonomyDataMessage") {
                sendUpdatedData();
            }
            else if (action === "debugger") {
                debugger;
            }
            else {
                return `Unexpected command type: ${action}`;
            }
        } catch (e) {
            console.log(e);
            console.log(`Exception caught with command: ${action}, data: ${data}`);
        }
        return "OK";
    },
};
