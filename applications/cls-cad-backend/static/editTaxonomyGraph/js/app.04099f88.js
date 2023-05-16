(function () {
  "use strict";
  var e = {
      9167: function (e, t, o) {
        var n = o(9242),
          a = o(1020),
          s = o(3396);
        function i(e, t, o, n, a, i) {
          const d = (0, s.up)("GraphWrapper");
          return (0, s.wg)(), (0, s.j4)(d);
        }
        function d(e, t, o, n, a, i) {
          const d = (0, s.up)("GraphContent");
          return (0, s.wg)(), (0, s.j4)(d);
        }
        var r = o(7139);
        const c = (e) => (
            (0, s.dD)("data-v-77702efa"), (e = e()), (0, s.Cn)(), e
          ),
          l = { id: "container", class: "h-screen" },
          h = {
            id: "nav-bar-top",
            class:
              "bg-background flex flex-row justify-between items-center h-8",
          },
          g = { class: "h-full" },
          m = c(() =>
            (0, s._)("div", { id: "cy", class: "bg-background" }, null, -1)
          );
        function u(e, t, o, n, a, i) {
          return (
            (0, s.wg)(),
            (0, s.iD)("div", l, [
              (0, s._)("div", h, [
                (0, s._)("div", null, (0, r.zw)(a.infoText), 1),
                (0, s._)("div", g, [
                  (0, s._)(
                    "button",
                    {
                      class:
                        "bg-button-blue hover:bg-button-hover text-white font-scada rounded font-medium h-full px-6 mr-2",
                      onClick:
                        t[0] ||
                        (t[0] = (...e) => i.relayout && i.relayout(...e)),
                    },
                    "Layout"
                  ),
                ]),
              ]),
              m,
            ])
          );
        }
        o(7658);
        var y = o(2584),
          p = o.n(y);
        class f {
          color(e, t) {
            e
              .style()
              .selector(".eh-preview, .eh-ghost-edge")
              .style({ "line-color": t }),
              e.style().selector(".eh-source").style({ "border-color": t }),
              e
                .style()
                .selector(".eh-target")
                .style({ "background-color": t, "border-color": "gray" }),
              e
                .style()
                .selector(".eh-ghost-edge.eh-preview-active")
                .style({ opacity: 0 });
          }
        }
        var N = new f();
        function v(e, t, o) {
          console.log("source: ", e, " target: ", t);
          let n = Object.assign(
            ...Object.keys(o).map((e) => ({ [e]: o[e].map(String) }))
          );
          n[e].push(t);
          let a = Object.keys(n).map((e) => [e]);
          while (a.length) {
            const e = [];
            for (const t of a) {
              const o = n[t[0]] || [];
              for (const n of o) {
                if (n === t[t.length - 1]) return !0;
                e.push([n, ...t]);
              }
            }
            a = e;
          }
          return !1;
        }
        (0, a.Q_)("HistoryStore", {
          state: () => ({ taxonomyHistory: [] }),
          actions: {
            addHistoryEntry(e) {
              this.taxonomyHistory.push(JSON.parse(JSON.stringify(e)));
            },
            printInfo() {
              console.log("history info:"),
                console.log("length: ", this.taxonomyHistory.length),
                this.taxonomyHistory.forEach((e, t) => {
                  console.log("entry ", t), console.table(e);
                });
            },
          },
          getters: {
            getLastState: (e) =>
              JSON.parse(JSON.stringify(e.taxonomyHistory.pop())),
            getPosition: (e) => e.taxonomyHistory.length,
          },
        });
        let x, b;
        class w {
          static drawEdge(e, t, o, n, a) {
            console.log(n);
            const s = o.$("node[name='" + e + "']");
            n.enableDrawMode(),
              n.start(s),
              o.on("cxttap", () => {
                n.drawMode && (n.disableDrawMode(), n.stop());
              }),
              o.on("ehhoverover", (e, t, n) => {
                let s = v(t.data().name, n.data().name, a);
                s
                  ? (console.log("circle found"), N.color(o, "red"), (x = !1))
                  : void 0 === n.data().name
                  ? (N.color(o, "purple"), (x = !1))
                  : (console.log("green arrow"), N.color(o, "green"), (x = !0));
              }),
              o.on("ehcomplete", (e, n, s, i) => {
                console.log("stopped edgecreation"),
                  console.log(
                    "event:",
                    e,
                    "\nsource: ",
                    n.data().name,
                    "\ntarget: ",
                    s.data().name,
                    "\nadded: ",
                    i.source().data().name,
                    "->",
                    i.target().data().name
                  ),
                  x
                    ? x &&
                      void 0 !== s.data().name &&
                      (void 0 !== b
                        ? (this.recoverEdge(o, a), this.removeEdge(o, b, a, !0))
                        : (a[n.data().name].push(s.data().name),
                          adsk
                            .fusionSendData(
                              "taxonomyDataMessage",
                              JSON.stringify(a)
                            )
                            .then((e) => console.log(e))),
                      o
                        .$(
                          "edge[source='" +
                            n.id() +
                            "'][target='" +
                            s.id() +
                            "']"
                        )
                        .data(
                          "name",
                          i.source().data().name + "->" + i.target().data().name
                        ))
                    : (console.log("remove invalid edge"),
                      o.remove(
                        "edge[source='" + n.id() + "'][target='" + s.id() + "']"
                      ),
                      t && this.recoverEdge(o, a));
              }),
              o.on("ehcancel", () => {
                console.log("cancelled"), t && this.recoverEdge(o, a);
              }),
              o.on("ehstop", () => {
                console.log("stopped."),
                  (t = !1),
                  (b = void 0),
                  n.disableDrawMode(),
                  n.stop(),
                  o.off("ehstart"),
                  o.off("ehcomplete"),
                  o.off("ehhoverover"),
                  o.off("ehhoverout"),
                  o.off("ehcancel"),
                  o.off("ehstop"),
                  o.off("cxttap");
              });
          }
          static initTmpEdge(e) {
            b = e;
          }
          static getAllEdges(e, t) {
            const o = e.edges("[source='" + t + "']");
            return (
              e.edges("[target='" + t + "']").forEach((e) => {
                o.push(e);
              }),
              o
            );
          }
          static getSourceEdges(e, t) {
            return e.edges("[source='" + t + "']");
          }
          static getTargetEdges(e, t) {
            return e.edges("[target='" + t + "']");
          }
          static removeEdge(e, t, o) {
            let n = t.source().data().name,
              a = t.target().data().name;
            o[n].splice(o[n].indexOf(a), 1),
              e.remove("edge[name='" + t.data().name + "']"),
              adsk
                .fusionSendData("taxonomyDataMessage", JSON.stringify(o))
                .then((e) => console.log(e));
          }
          static recoverEdge(e, t) {
            e.add({
              group: "edges",
              data: {
                source: b.source().data().name,
                target: b.target().data().name,
                name: b.source().data().name + "->" + b.target().data().name,
              },
            }),
              t[b.source().data().name].push(b.target().data().name),
              adsk
                .fusionSendData("taxonomyDataMessage", JSON.stringify(t))
                .then((e) => console.log(e));
          }
        }
        var k = w;
        let E = {
          canConnect: function (e, t) {
            return e.id() !== t.id();
          },
          hoverDelay: 150,
          snap: !0,
          snapThreshold: 15,
          snapFrequency: 15,
          noEdgeEventsInDraw: !0,
          disableBrowserGestures: !0,
        };
        var D = JSON.parse(
            '[{"selector":".node","style":{"label":"data(name)","text-valign":"center","color":"black","background-image":"url(\'./icons/icon-node.png\')","background-clip":"none","background-width":"50px","background-height":"50px","background-color":"transparent","background-opacity":"0","font-family":"Scada-Regular","width":"label","height":"50px","padding":"5px"}},{"selector":".creatingnode","style":{"label":"data(name)","text-valign":"center","color":"black","background-image":"url(\'./icons/icon-node.png\')","background-clip":"none","background-width":"50px","background-height":"50px","background-color":"transparent","background-opacity":"0","font-family":"Scada-Regular","width":"50px","height":"50px","padding":"5px"}},{"selector":".AnyPart","style":{"label":"data(name)","text-valign":"center","color":"black","background-color":"transparent","background-image":"url(\'./icons/icon-root.png\')","background-clip":"none","background-width":"50px","background-height":"50px","background-opacity":"0","font-family":"Scada-Regular","width":"label","height":"50px","padding":"8px"}},{"selector":".highlightNode","style":{"label":"data(name)","text-valign":"center","color":"black","background-color":"#ef4444","font-family":"Scada-Regular","shape":"diamond","width":"50px","height":"50px"}},{"selector":".highlightNodeWithoutOptions","style":{"label":"data(name)","text-valign":"center","color":"black","background-color":"#ef4444","font-family":"Scada-Regular","shape":"diamond","width":"50px","height":"50px","taxi-turn-min-distance":"20px"}},{"selector":"edge","style":{"width":4,"target-arrow-shape":"triangle","source-arrow-shape":"diamond","line-color":"#706a6a","target-arrow-color":"#222222","curve-style":"taxi","taxi-direction":"downward","taxi-turn":"30px"}},{"selector":".eh-source","style":{"border-width":2}},{"selector":".eh-target","style":{"border-width":2}},{"selector":".eh-preview, .eh-ghost-edge","style":{"line-color":"purple"}}]'
          ),
          M = {
            name: "GraphContent",
            inject: ["taxonomyDataMessage"],
            setup() {},
            data() {
              return {
                infoText: "",
                cyNodes: [],
                cyEdges: [],
                taxonomyString: this.taxonomyDataMessage,
                taxonomyData: void 0,
                undoFlag: !1,
                taxonomyID: void 0,
                eh: void 0,
                nodeMenu: void 0,
                edgeMenu: void 0,
                coreMenu: void 0,
                renameMenu: void 0,
                renameMenuFlag: !1,
                cacheNode: void 0,
                oldNodeName: void 0,
                newNodeName: void 0,
                ascIndex: 0,
                position: void 0,
                oldNode: void 0,
              };
            },
            mounted() {
              this.setTaxonomyData(JSON.parse(this.taxonomyString)),
                (this.taxonomyID = this.taxonomyData.ID);
            },
            methods: {
              setTaxonomyData: function (e) {
                (this.taxonomyData = e),
                  (this.cyNodes = []),
                  (this.cyEdges = []);
                for (let [o, n] of Object.entries(this.taxonomyData))
                  this.cyNodes.push({ data: { id: o, name: o } }),
                    n.forEach((e) => {
                      this.cyEdges.push({
                        data: { source: o, target: e, name: o + "->" + e },
                      });
                    });
                (this.cy = p()({
                  container: document.getElementById("cy"),
                  elements: { nodes: this.cyNodes, edges: this.cyEdges },
                  style: D,
                })),
                  this.cy.nodes().addClass("node"),
                  this.cy.$("node[name='Format']").classes("AnyPart"),
                  this.cy.$("node[name='Part']").classes("AnyPart"),
                  this.cy.$("node[name='Attribute']").classes("AnyPart"),
                  this.initNodeMenu(),
                  this.initEdgeMenu(),
                  this.initCoreMenu(),
                  (this.eh = this.cy.edgehandles(E)),
                  this.relayout(),
                  1 == Object.keys(this.taxonomyData).length &&
                    this.cy.center(this.cy.nodes()[0]);
                let t = this;
                this.cy.on("cxttapstart", function (e) {
                  t.position = e.renderedPosition;
                });
              },
              initNodeMenu: function () {
                this.nodeMenu = this.cy.cxtmenu({
                  menuRadius: 75,
                  selector: "node",
                  commands: [
                    {
                      fillColor: "rgba(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background:
                          "url('./icons/arrow-turn-down-solid.svg') no-repeat center",
                        backgroundSize: "30px 30px",
                      },
                      select: (e) => {
                        console.log(this.nodeMenu),
                          this.drawEdge(e.data().name, !1);
                      },
                    },
                    {
                      fillColor: "rgba(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background:
                          "url('./icons/pen-solid.svg') no-repeat center",
                        backgroundSize: "30px 30px",
                      },
                      select: (e) => {
                        this.renameNode(e.data().name);
                      },
                    },
                    {
                      fillColor: "rgb(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background:
                          "url('./icons/trash-solid.svg') no-repeat center",
                        backgroundSize: "30px 30px",
                      },
                      select: (e) => {
                        this.removeNode(e.data().name);
                      },
                    },
                  ],
                  openMenuEvents: "cxttapstart taphold",
                });
              },
              initEdgeMenu: function () {
                this.edgeMenu = this.cy.cxtmenu({
                  menuRadius: 75,
                  selector: "edge",
                  commands: [
                    {
                      fillColor: "rgb(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background:
                          "url('./icons/trash-solid.svg') no-repeat center",
                        backgroundSize: "30px 30px",
                      },
                      select: (e) => {
                        console.log("deleteEdge"),
                          k.removeEdge(this.cy, e, this.taxonomyData);
                      },
                    },
                    {
                      fillColor: "rgb(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background:
                          "url('./icons/arrow-down-a-z-solid.svg') no-repeat center",
                        backgroundSize: "30px 30px",
                      },
                      select: (e) => {
                        k.initTmpEdge(e),
                          k.removeEdge(this.cy, e, this.taxonomyData);
                        let t = e.source().data().name;
                        this.drawEdge(t, !0);
                      },
                    },
                  ],
                  openMenuEvents: "cxttapstart taphold",
                });
              },
              initCoreMenu: function () {
                this.coreMenu = this.cy.cxtmenu({
                  menuRadius: 75,
                  selector: "core",
                  commands: [
                    {
                      fillColor: "rgb(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background:
                          "url('./icons/diamond-solid.svg') no-repeat center",
                        backgroundSize: "30px 30px",
                      },
                      select: () => {
                        this.createNode();
                      },
                    },
                  ],
                  openMenuEvents: "cxttapstart taphold",
                });
              },
              initRenameMenu: function () {
                this.renameMenu = this.cy.cxtmenu({
                  selector: ".highlightNode",
                  menuRadius: 75,
                  commands: [
                    {
                      fillColor: "rgb(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background:
                          "url('./icons/pen-solid.svg') no-repeat center",
                        backgroundSize: "30px 30px",
                      },
                      select: (e) => {
                        this.renameNode(e.data().name);
                      },
                    },
                    {
                      fillColor: "rgb(200, 200, 200, 0.75)",
                      content: "",
                      contentStyle: {
                        background: "url('./icons/diamond-solid.svg') ",
                        backgroundRepeat: "no-repeat round",
                        backgroundPositionX: "center",
                        backgroundSize: "50%",
                      },
                      select: (e) => {
                        console.log("merge", e), this.mergeNodes(e.data().name);
                      },
                    },
                  ],
                  openMenuEvents: "cxttapstart taphold",
                });
              },
              drawEdge: function (e, t) {
                k.drawEdge(e, t, this.cy, this.eh, this.taxonomyData);
              },
              createNode: function () {
                (this.newNodeName = "newNode" + this.ascIndex),
                  this.ascIndex++,
                  console.log(this.position);
                let e = this.cy.add({
                  data: { id: this.newNodeName, name: this.newNodeName },
                  renderedPosition: this.position,
                });
                this.cy
                  .$("node[name='" + this.newNodeName + "']")
                  .addClass("creatingnode"),
                  (this.taxonomyData[this.newNodeName] = []),
                  this.renameNode(e.data().name);
              },
              renameNode: function (e) {
                (this.oldNodeName = e),
                  this.cy
                    .$("node[name='" + this.oldNodeName + "']")
                    .json({ data: { shadowName: this.oldNodeName } }),
                  this.cy
                    .$("node[name='" + this.oldNodeName + "']")
                    .json({ data: { name: "" } }),
                  (this.newNodeName = ""),
                  document.addEventListener("keydown", this.renameEvent, !1);
              },
              renameEvent: function (e) {
                const t = e.key;
                1 === t.length &&
                  ((this.newNodeName += t),
                  this.cy
                    .$("node[shadowName='" + this.oldNodeName + "']")
                    .json({ data: { name: this.newNodeName } })),
                  ("Backspace" !== t && "Delete" !== t) ||
                    ((this.newNodeName = this.newNodeName.slice(0, -1)),
                    this.cy
                      .$("node[shadowName='" + this.oldNodeName + "']")
                      .json({ data: { name: this.newNodeName } })),
                  "Enter" === t &&
                    (this.newNodeName.length > 0
                      ? (this.cy
                          .$("node[shadowName='" + this.oldNodeName + "']")
                          .json({ data: { name: this.oldNodeName } }),
                        document.removeEventListener(
                          "keydown",
                          this.renameEvent,
                          !1
                        ),
                        this.rename({
                          newName: this.newNodeName,
                          oldName: this.oldNodeName,
                        }))
                      : (this.cy
                          .$("node[shadowName='" + this.oldNodeName + "']")
                          .json({ data: { name: this.oldNodeName } }),
                        document.removeEventListener(
                          "keydown",
                          this.renameEvent,
                          !1
                        ))),
                  "Escape" === t &&
                    (this.cy
                      .$("node[shadowName='" + this.oldNodeName + "']")
                      .json({ data: { name: this.oldNodeName } }),
                    document.removeEventListener(
                      "keydown",
                      this.renameEvent,
                      !1
                    ));
              },
              rename: function (e) {
                e.oldName !== e.newName &&
                  (void 0 !== this.taxonomyData[e.newName] &&
                  this.oldNode !== e.newName
                    ? (this.renameMenuFlag &&
                        this.cacheNode !== e.newName &&
                        this.cy
                          .$("node[name='" + this.cacheNode + "']")
                          .classes("node"),
                      this.renameMenuFlag ||
                        ((this.oldNode = e.oldName), this.nodeMenu.destroy()),
                      this.cy
                        .$("node[name='" + e.oldName + "']")
                        .classes("highlightNode"),
                      this.cy
                        .$("node[name='" + e.newName + "']")
                        .classes("highlightNodeWithoutOptions"),
                      (this.renameMenuFlag = !0),
                      (this.cacheNode = e.newName),
                      this.initRenameMenu(),
                      this.cy
                        .$("[name='" + e.oldName + "']")
                        .json({ data: { name: "(" + e.newName + ")" } }))
                    : (console.log("renaming ", e.oldName, " to ", e.newName),
                      (this.taxonomyData[e.newName] = []),
                      this.addEdges(e.oldName, e.newName, this.taxonomyData),
                      delete this.taxonomyData[e.oldName],
                      this.cy
                        .$("[name='" + e.oldName + "']")
                        .json({ data: { name: e.newName } }),
                      this.renameMenuFlag &&
                        (this.cy
                          .$("node[name='" + this.cacheNode + "']")
                          .classes("node"),
                        this.cy
                          .$("node[name='" + e.newName + "']")
                          .classes("node"),
                        (this.oldNode = void 0),
                        (this.renameMenuFlag = !1),
                        (this.cacheNode = void 0),
                        this.renameMenu.destroy(),
                        this.initNodeMenu()),
                      console.table(this.taxonomyData),
                      this.renamef360(e.oldName, e.newName),
                      this.save()),
                  this.cy
                    .$("node[name='" + e.newName + "']")
                    .removeClass("creatingnode"),
                  this.cy.$("node[name='" + e.newName + "']").addClass("node"));
              },
              removeNode: function (e) {
                const t = k.getAllEdges(this.cy, e);
                t.length > 0 &&
                  t.forEach((e) => {
                    let t = e.source().data().name,
                      o = e.target().data().name;
                    this.cy.remove(
                      "edge[source='" + t + "'][target='" + o + "']"
                    ),
                      this.taxonomyData[t].splice(
                        this.taxonomyData[t].indexOf(o),
                        1
                      );
                  }),
                  this.cy
                    .$("node[name='" + e + "']")
                    .animate({ style: { opacity: 0.5 } }),
                  setTimeout(() => {
                    this.cy.remove("node[name='" + e + "']"),
                      delete this.taxonomyData[e],
                      this.save();
                  }, 300);
              },
              mergeNodes: function (e) {
                const t = e.substring(1, e.length - 1),
                  o = this.cy.$("node[name='" + e + "']");
                console.log("bracket node: ", o);
                const n = k.getSourceEdges(this.cy, o.id());
                console.log("cyOriginNodeChildren: ", n),
                  n.length > 0 &&
                    n.forEach((e) => {
                      let o =
                        this.cy.$(
                          "edge[name='" +
                            t +
                            "->" +
                            e.target().data().name +
                            "']"
                        ).length > 0;
                      if (!o) {
                        this.cy.add({
                          group: "edges",
                          data: {
                            source: t,
                            target: e.target().data().name,
                            name: t + "->" + e.target().data().name,
                          },
                        });
                        let o = e.target().data().name;
                        this.taxonomyData[t].push(o),
                          console.log("added: ", t, "->", o);
                      }
                    });
                const a = k.getTargetEdges(this.cy, o.id());
                a.length > 0 &&
                  a.forEach((e) => {
                    console.log("is edge already there? ");
                    let o = e.source().data().name,
                      n = this.taxonomyData[o].indexOf(this.oldNode);
                    -1 !== n &&
                      (console.log("removing ", this.oldNode, " from ", o),
                      this.taxonomyData[o].splice(n, 1));
                    let a =
                      this.cy.$("edge[name='" + o + "->" + t + "']").length > 0;
                    a ||
                      (this.cy.add({
                        group: "edges",
                        data: {
                          source: e.source().data().name,
                          target: t,
                          name: e.source().data().name + "->" + t,
                        },
                      }),
                      this.taxonomyData[o].push(t),
                      console.log("added: ", o, "->", t));
                  }),
                  delete this.taxonomyData[this.oldNode],
                  this.cy.$("node[name='" + t + "']").classes("node"),
                  this.cy.remove("node[name='" + e + "']"),
                  this.renameMenu.destroy(),
                  this.nodeMenu.destroy(),
                  this.initNodeMenu(),
                  (this.oldNode = void 0),
                  (this.cacheNode = void 0),
                  (this.renameMenuFlag = !1),
                  this.setTaxonomyData(this.taxonomyData),
                  this.save();
              },
              addEdges: function (e, t, o) {
                const n = this.cy.$("node[name='" + e + "']").connectedEdges();
                n.forEach((n) => {
                  let a = n.source().data().name,
                    s = n.target().data().name;
                  if (s === e)
                    if (
                      (console.log("parent found (", a, ")"),
                      n.json({ data: { name: a + "->" + t, target: t } }),
                      void 0 !== this.oldNode)
                    ) {
                      let e = o[a].indexOf(this.oldNode);
                      o[a][e] = t;
                    } else {
                      let n = o[a].indexOf(e);
                      o[a][n] = t;
                    }
                  else
                    console.log("child found (", s, ")"),
                      n.json({ data: { name: t + "->" + s } }),
                      o[t].push(s);
                }),
                  this.save();
              },
              json: function () {
                console.log(this.$root);
              },
              save: function () {
                adsk
                  .fusionSendData(
                    "taxonomyDataMessage",
                    JSON.stringify(this.taxonomyData)
                  )
                  .then((e) => console.log(e));
              },
              renamef360: function (e, t) {
                let o = [e, t],
                  n = JSON.stringify(o);
                adsk
                  .fusionSendData("renameDataNotification", n)
                  .then((e) => console.log(e));
              },
              relayout: function () {
                let e = {
                  spacingFactor: 0.9,
                  nodeDimensionsIncludeLabels: !0,
                  animate: !0,
                  animationDuration: 500,
                  fit: Object.keys(this.taxonomyData).length > 1,
                  padding: 0,
                };
                this.cy.layout({ name: "dagre", defaults: e }).run();
              },
            },
          },
          S = o(89);
        const O = (0, S.Z)(M, [
          ["render", u],
          ["__scopeId", "data-v-77702efa"],
        ]);
        var $ = O,
          j = { name: "GraphWrapper", components: { GraphContent: $ } };
        const C = (0, S.Z)(j, [["render", d]]);
        var T = C,
          _ = { name: "App", components: { GraphWrapper: T } };
        const I = (0, S.Z)(_, [["render", i]]);
        var P = I,
          F = o(9253),
          J = o.n(F),
          R = o(1454),
          z = o.n(R),
          H = o(1590),
          A = o.n(H);
        const G = (0, a.WB)(),
          L = (0, n.ri)(P);
        L.use(G),
          (window.fusionJavaScriptHandler = {
            handle: function (e, t) {
              try {
                if ("updateMessage" === e) console.log("updated");
                else if ("taxonomyDataMessage" === e)
                  console.log("TaxonomyData arrived."),
                    void 0 === L.config.globalProperties.cy &&
                      ((L.config.globalProperties.cy = p()),
                      p().use(J()),
                      p().use(z()),
                      p().use(A())),
                    0 === Object.keys(L._context.provides).length &&
                      L.provide("taxonomyDataMessage", t),
                    null === L._instance && L.mount("#app");
                else if ("taxonomyIDMessage" === e)
                  console.log("taxonomyIDMessage arrived."),
                    (document.title = t);
                else {
                  if ("debugger" !== e)
                    return (
                      console.log("testelse"), `Unexpected command type: ${e}`
                    );
                  console.log("testdebugger");
                }
              } catch (o) {
                console.log(o),
                  console.log(
                    `Exception caught with command: ${e}, data: ${t}`
                  );
              }
              return "OK";
            },
          });
      },
    },
    t = {};
  function o(n) {
    var a = t[n];
    if (void 0 !== a) return a.exports;
    var s = (t[n] = { id: n, loaded: !1, exports: {} });
    return e[n].call(s.exports, s, s.exports, o), (s.loaded = !0), s.exports;
  }
  (o.m = e),
    (function () {
      var e = [];
      o.O = function (t, n, a, s) {
        if (!n) {
          var i = 1 / 0;
          for (l = 0; l < e.length; l++) {
            (n = e[l][0]), (a = e[l][1]), (s = e[l][2]);
            for (var d = !0, r = 0; r < n.length; r++)
              (!1 & s || i >= s) &&
              Object.keys(o.O).every(function (e) {
                return o.O[e](n[r]);
              })
                ? n.splice(r--, 1)
                : ((d = !1), s < i && (i = s));
            if (d) {
              e.splice(l--, 1);
              var c = a();
              void 0 !== c && (t = c);
            }
          }
          return t;
        }
        s = s || 0;
        for (var l = e.length; l > 0 && e[l - 1][2] > s; l--) e[l] = e[l - 1];
        e[l] = [n, a, s];
      };
    })(),
    (function () {
      o.n = function (e) {
        var t =
          e && e.__esModule
            ? function () {
                return e["default"];
              }
            : function () {
                return e;
              };
        return o.d(t, { a: t }), t;
      };
    })(),
    (function () {
      o.d = function (e, t) {
        for (var n in t)
          o.o(t, n) &&
            !o.o(e, n) &&
            Object.defineProperty(e, n, { enumerable: !0, get: t[n] });
      };
    })(),
    (function () {
      o.g = (function () {
        if ("object" === typeof globalThis) return globalThis;
        try {
          return this || new Function("return this")();
        } catch (e) {
          if ("object" === typeof window) return window;
        }
      })();
    })(),
    (function () {
      o.o = function (e, t) {
        return Object.prototype.hasOwnProperty.call(e, t);
      };
    })(),
    (function () {
      o.nmd = function (e) {
        return (e.paths = []), e.children || (e.children = []), e;
      };
    })(),
    (function () {
      var e = { 143: 0 };
      o.O.j = function (t) {
        return 0 === e[t];
      };
      var t = function (t, n) {
          var a,
            s,
            i = n[0],
            d = n[1],
            r = n[2],
            c = 0;
          if (
            i.some(function (t) {
              return 0 !== e[t];
            })
          ) {
            for (a in d) o.o(d, a) && (o.m[a] = d[a]);
            if (r) var l = r(o);
          }
          for (t && t(n); c < i.length; c++)
            (s = i[c]), o.o(e, s) && e[s] && e[s][0](), (e[s] = 0);
          return o.O(l);
        },
        n = (self["webpackChunkcls_cytoscape"] =
          self["webpackChunkcls_cytoscape"] || []);
      n.forEach(t.bind(null, 0)), (n.push = t.bind(null, n.push.bind(n)));
    })();
  var n = o.O(void 0, [998], function () {
    return o(9167);
  });
  n = o.O(n);
})();
//# sourceMappingURL=app.04099f88.js.map
