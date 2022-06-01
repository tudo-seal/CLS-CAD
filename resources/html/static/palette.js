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

function sendUpdatedData() {
    var nodes = $('#data').jstree(true).get_json('#', { flat: true })
    var returnData = {
        "ID": taxonomyID,
        "nodes": nodes
    }
    returnDataString = JSON.stringify(returnData)
    if (returnDataString !== taxonomyOriginalData) {
        adsk.fusionSendData("updateDataNotification", returnDataString).then((result) =>
            console.log(result)
        );
    }

}

function setTaxonomyData(taxonomyString) {
    const taxonomyData = JSON.parse(taxonomyString);
    taxonomyOriginalData = taxonomyString;
    taxonomyID = taxonomyData.ID;
    console.log(taxonomyID)
    console.log(taxonomyData.nodes)

    $('#data').jstree({
        'core': {
            'data': taxonomyData.nodes,
            'force_text': true,
            "check_callback": true
        },
        "search": {
            "show_only_matches": true,
            "show_only_matches_children": true,
            "case_sensitive": true,
        },
        "contextmenu": {
            "items": function (node) {
                if (node.parents.length < 2) {
                    return {
                        "rename": {
                            label: "Rename",
                            action: function (data) {
                                var inst = $.jstree.reference(data.reference),
                                    obj = inst.get_node(data.reference);
                                inst.edit(obj);
                                inst.sort(inst.get_node(obj.parent))
                            }
                        },
                        "create": {
                            label: "Create New",
                            action: function (data) {
                                var inst = $.jstree.reference(data.reference),
                                    obj = inst.get_node(data.reference);
                                inst.create_node(obj, {}, "last", function (new_node) {
                                    try {
                                        inst.edit(new_node);
                                    } catch (ex) {
                                        setTimeout(function () { inst.edit(new_node); }, 0);
                                    }
                                });
                            }
                        },
                    }
                }
                return {
                    "rename": {
                        label: "Rename",
                        action: function (data) {
                            var inst = $.jstree.reference(data.reference),
                                obj = inst.get_node(data.reference);
                            inst.edit(obj);
                            inst.sort(inst.get_node(obj.parent))
                        }
                    },
                    "create": {
                        label: "Create New",
                        action: function (data) {
                            var inst = $.jstree.reference(data.reference),
                                obj = inst.get_node(data.reference);
                            inst.create_node(obj, {}, "last", function (new_node) {
                                try {
                                    inst.edit(new_node);
                                } catch (ex) {
                                    setTimeout(function () { inst.edit(new_node); }, 0);
                                }
                            });
                        }
                    },
                    "remove": {
                        label: "Delete",
                        action: function (data) {
                            var inst = $.jstree.reference(data.reference),
                                obj = inst.get_node(data.reference);
                            if (inst.is_selected(obj)) {
                                inst.delete_node(inst.get_selected());
                            }
                            else {
                                inst.delete_node(obj);
                            }
                        },
                        separator_before: true
                    }
                }
            }
        },
        "plugins": [
            "contextmenu", "dnd", "search", "unique",
            "types", "wholerow", "sort"
        ]
    });

    var to = false;
    $('#taxonomy_search').keyup(function () {
        if (to) { clearTimeout(to); }
        to = setTimeout(function () {
            var v = $('#taxonomy_search').val();
            $('#data').jstree(true).search(v);
        }, 250);
    });

    $('#data').on('create_node.jstree', function (node, parent, position) {
        console.log("Created")
    });

    $('#data').on('rename_node.jstree', function (node, text, old) {
        sendUpdatedData();
        console.log("Renamed")
    });

    $('#data').on('delete_node.jstree', function (node, parent) {
        sendUpdatedData();
        console.log("Deleted")
    });

    $('#data').on('select_node.jstree', function (node, selected, event) {
        console.log(node)
        console.log(selected)
        const args = {
            arg1: selected.node.id,
            arg2: selected.node.text
        };

        adsk.fusionSendData("messageFromPalette", JSON.stringify(args)).then((result) =>
            () => { }
            // Potetially do stuff
        );
    });
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
