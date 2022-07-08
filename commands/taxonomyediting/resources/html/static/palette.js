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

var taxonomyID;
var taxonomyOriginalData;
var taxonomyData;

var populated = false;

function setTaxonomyData(taxonomyString) {
    var cynodes = [];
    var cyedges = [];

    taxonomyData = JSON.parse(taxonomyString);
    taxonomyOriginalData = taxonomyString;
    taxonomyID = taxonomyData.ID;
    populated = true;


    for (let [key, value] of Object.entries(taxonomyData)) {
        cynodes.push({ data: { id: key } });
        value.forEach(child => {
            cyedges.push({ data: { source: key, target: child } })
        });
    }

    var cy = window.cy = cytoscape({
        container: document.getElementById('cy'),

        boxSelectionEnabled: false,
        autounselectify: true,

        layout: {
            name: 'dagre',
            spacingFactor: 1.5
        },

        style: [
            {
                selector: 'node',
                style: {
                    'label': 'data(id)',
                    'text-valign': 'center',
                    'color': '#000000',
                    'background-color': '#639a00',
                    'font-family': 'Courier, monospace',
                    'font-weight': '900'
                }
            }
        ],

        elements: {
            nodes: cynodes,
            edges: cyedges
        }
    });
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
            } else if (action === "taxonomyDataMessage") {
                console.log("TaxonomyData arrived.")
                setTaxonomyData(data);
            } else if (action === "taxonomyIDMessage") {
                document.title = data;
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
