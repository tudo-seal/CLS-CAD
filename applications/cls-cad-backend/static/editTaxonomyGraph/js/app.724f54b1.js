(function () {
  "use strict";
  var e = {
      3214: function (e, t, o) {
        var n = o(9242),
          a = o(1020),
          s = o(3396);
        function r(e, t, o, n, a, r) {
          const d = (0, s.up)("GraphWrapper");
          return (0, s.wg)(), (0, s.j4)(d);
        }
        function d(e, t, o, n, a, r) {
          const d = (0, s.up)("GraphContent");
          return (0, s.wg)(), (0, s.j4)(d);
        }
        var i = o(7139);
        const c = (e) => (
            (0, s.dD)("data-v-b24b4c4a"), (e = e()), (0, s.Cn)(), e
          ),
          l = { id: "container", class: "h-screen" },
          h = {
            id: "nav-bar-top",
            class:
              "bg-background flex flex-row justify-between items-center h-8",
          },
          m = { class: "h-full" },
          g = c(() =>
            (0, s._)("div", { id: "cy", class: "bg-background" }, null, -1)
          );
        function u(e, t, o, n, a, r) {
          return (
            (0, s.wg)(),
            (0, s.iD)("div", l, [
              (0, s._)("div", h, [
                (0, s._)("div", null, (0, i.zw)(a.infoText), 1),
                (0, s._)("div", m, [
                  n.historyStore.getPosition > 0
                    ? ((0, s.wg)(),
                      (0, s.iD)(
                        "button",
                        {
                          key: 0,
                          class:
                            "bg-button-blue hover:bg-button-hover text-white font-scada rounded font-medium h-full px-6 mr-2",
                          onClick:
                            t[0] || (t[0] = (...e) => r.undo && r.undo(...e)),
                        },
                        " Undo "
                      ))
                    : (0, s.kq)("", !0),
                  (0, s._)(
                    "button",
                    {
                      class:
                        "bg-button-blue hover:bg-button-hover text-white font-scada rounded font-medium h-full px-6 mr-2",
                      onClick:
                        t[1] || (t[1] = (...e) => r.save && r.save(...e)),
                    },
                    "Save"
                  ),
                ]),
              ]),
              g,
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
        var x = new f();
        function N(e, t, o) {
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
        const v = (0, a.Q_)("HistoryStore", {
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
        let b, w;
        class E {
          static drawEdge(e, t, o, n, a) {
            console.log(n);
            const s = o.$("node[name='" + e + "']"),
              r = v();
            n.enableDrawMode(),
              n.start(s),
              o.on("cxttap", () => {
                n.drawMode && (n.disableDrawMode(), n.stop());
              }),
              o.on("ehhoverover", (e, t, n) => {
                let s = N(t.data().name, n.data().name, a);
                s
                  ? (console.log("circle found"), x.color(o, "red"), (b = !1))
                  : void 0 === n.data().name
                  ? (x.color(o, "purple"), (b = !1))
                  : (console.log("green arrow"), x.color(o, "green"), (b = !0));
              }),
              o.on("ehcomplete", (e, n, s, d) => {
                console.log("stopped edgecreation"),
                  console.log(
                    "event:",
                    e,
                    "\nsource: ",
                    n.data().name,
                    "\ntarget: ",
                    s.data().name,
                    "\nadded: ",
                    d.source().data().name,
                    "->",
                    d.target().data().name
                  ),
                  b
                    ? b &&
                      void 0 !== s.data().name &&
                      (void 0 !== w
                        ? (this.recoverEdge(o, a),
                          r.addHistoryEntry(a),
                          this.removeEdge(o, w, a, !0))
                        : (r.addHistoryEntry(a),
                          a[n.data().name].push(s.data().name)),
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
                          d.source().data().name + "->" + d.target().data().name
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
                  (w = void 0),
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
            w = e;
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
          static removeEdge(e, t, o, n) {
            if (!n) {
              const e = v();
              e.addHistoryEntry(o);
            }
            let a = t.source().data().name,
              s = t.target().data().name;
            o[a].splice(o[a].indexOf(s), 1),
              e.remove("edge[name='" + t.data().name + "']");
          }
          static recoverEdge(e, t) {
            e.add({
              group: "edges",
              data: {
                source: w.source().data().name,
                target: w.target().data().name,
                name: w.source().data().name + "->" + w.target().data().name,
              },
            }),
              t[w.source().data().name].push(w.target().data().name);
          }
        }
        var k = E;
        let D = {
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
        var M = JSON.parse(
            '[{"selector":".node","style":{"label":"data(name)","text-valign":"center","color":"black","background-image":"url(\'./icons/icon-node.png\')","background-clip":"none","background-width":"50px","background-height":"50px","shape":"diamond","background-color":"#6896c8","font-family":"Scada-Regular","width":"40px","height":"50px"}},{"selector":".AnyPart","style":{"label":"data(name)","text-valign":"center","color":"black","background-color":"#909090","background-image":"url(\'./icons/icon-root.png\')","background-clip":"none","background-width":"50px","background-height":"50px","shape":"diamond","font-family":"Scada-Regular","width":"40px","height":"50px"}},{"selector":".highlightNode","style":{"label":"data(name)","text-valign":"center","color":"black","background-color":"#ef4444","font-family":"Scada-Regular","shape":"diamond","width":"50px","height":"50px"}},{"selector":".highlightNodeWithoutOptions","style":{"label":"data(name)","text-valign":"center","color":"black","background-color":"#ef4444","font-family":"Scada-Regular","shape":"diamond","width":"50px","height":"50px","taxi-turn-min-distance":"20px"}},{"selector":"edge","style":{"width":4,"target-arrow-shape":"triangle","source-arrow-shape":"diamond","line-color":"#706a6a","target-arrow-color":"#222222","curve-style":"taxi","taxi-direction":"downward","taxi-turn":"30px"}},{"selector":".eh-source","style":{"border-width":2}},{"selector":".eh-target","style":{"border-width":2}},{"selector":".eh-preview, .eh-ghost-edge","style":{"line-color":"purple"}}]'
          ),
          S = {
            name: "GraphContent",
            inject: ["taxonomyDataMessage"],
            setup() {
              const e = v();
              return { historyStore: e };
            },
            data() {
              return {
                infoText: "Headlinewrapper (only for debugging)",
                cyNodes: [],
                cyEdges: [],
                taxonomyString: this.taxonomyDataMessage,
                taxonomyData: void 0,
                taxonomyDataHistory: [],
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
                for (let [n, a] of Object.entries(this.taxonomyData))
                  this.cyNodes.push({ data: { id: n, name: n } }),
                    a.forEach((e) => {
                      this.cyEdges.push({
                        data: { source: n, target: e, name: n + "->" + e },
                      });
                    });
                (this.cy = p()({
                  container: document.getElementById("cy"),
                  layout: { name: "dagre", fit: !0, spacingFactor: 1.5 },
                  style: M,
                  elements: { nodes: this.cyNodes, edges: this.cyEdges },
                })),
                  this.cy.nodes().addClass("node"),
                  this.cy.$("node[name='AnyPart']").classes("AnyPart");
                let t = this.cy.$("node[name.length > 16]"),
                  o = {};
                t.forEach((e) => {
                  let t = e.position("x"),
                    n = e.position("y");
                  void 0 !== o[n]
                    ? o[n].push({ name: e.data().name, x: t })
                    : (o[n] = [{ name: e.data().name, x: t }]);
                }),
                  Object.entries(o).forEach((e) => {
                    if (e[1].length > 1) {
                      e[1].sort((e, t) => e.x - t.x);
                      let t = this.cy.$("node[name='" + e[1][0].name + "']");
                      t.shift({ x: -2 * e[1][0].name.length });
                      while (t.outgoers("node").length > 0)
                        t.outgoers("node").forEach((o) => {
                          o.shift({ x: -2 * e[1][0].name.length }), (t = o);
                        });
                      let o = this.cy.$(
                        "node[name='" + e[1][e[1].length - 1].name + "']"
                      );
                      o.shift({ x: 2 * e[1][e[1].length - 1].name.length });
                      while (o.outgoers("node").length > 0)
                        o.outgoers("node").forEach((t) => {
                          t.shift({ x: 2 * e[1][e[1].length - 1].name.length }),
                            (o = t);
                        });
                    } else console.log("no pair");
                  }),
                  this.initNodeMenu(),
                  this.initEdgeMenu(),
                  this.initCoreMenu(),
                  (this.eh = this.cy.edgehandles(D));
              },
              initNodeMenu: function () {
                this.nodeMenu = this.cy.cxtmenu({
                  menuRadius: 75,
                  selector: ".node",
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
                        console.log("deleteEdge");
                        let t = !1;
                        k.removeEdge(this.cy, e, this.taxonomyData, t);
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
                        k.initTmpEdge(e);
                        let t = !0;
                        k.removeEdge(this.cy, e, this.taxonomyData, t);
                        let o = e.source().data().name;
                        this.drawEdge(o, !0);
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
                this.historyStore.addHistoryEntry(this.taxonomyData),
                  (this.newNodeName = "newNode" + this.ascIndex),
                  this.ascIndex++,
                  this.cy.add({
                    data: { id: this.newNodeName, name: this.newNodeName },
                  }),
                  this.cy
                    .$("node[name='" + this.newNodeName + "']")
                    .addClass("node"),
                  (this.taxonomyData[this.newNodeName] = []);
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
                      : alert(
                          this.oldNodeName + " cannot be renamed to nothing!"
                        )),
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
                    : (this.oldNode !== e.newName &&
                        this.historyStore.addHistoryEntry(this.taxonomyData),
                      console.log("renaming ", e.oldName, " to ", e.newName),
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
                      console.table(this.taxonomyData)));
              },
              removeNode: function (e) {
                this.historyStore.addHistoryEntry(this.taxonomyData);
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
                      delete this.taxonomyData[e];
                  }, 300);
              },
              mergeNodes: function (e) {
                this.historyStore.addHistoryEntry(this.taxonomyData);
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
                  this.setTaxonomyData(this.taxonomyData);
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
                });
              },
              undo: async function () {
                await console.table(this.historyStore.taxonomyHistory[0]);
                const e = this.historyStore.taxonomyHistory.pop();
                console.table(e), this.setTaxonomyData(e);
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
            },
          },
          O = o(89);
        const $ = (0, O.Z)(S, [
          ["render", u],
          ["__scopeId", "data-v-b24b4c4a"],
        ]);
        var j = $,
          C = { name: "GraphWrapper", components: { GraphContent: j } };
        const H = (0, O.Z)(C, [["render", d]]);
        var T = H,
          _ = { name: "App", components: { GraphWrapper: T } };
        const I = (0, O.Z)(_, [["render", r]]);
        var F = I,
          R = o(9253),
          z = o.n(R),
          P = o(1454),
          J = o.n(P),
          G = o(1590),
          A = o.n(G);
        const W = (0, a.WB)(),
          B = (0, n.ri)(F);
        B.use(W),
          (window.fusionJavaScriptHandler = {
            handle: function (e, t) {
              try {
                if ("updateMessage" === e) console.log("updated");
                else if ("taxonomyDataMessage" === e)
                  console.log("TaxonomyData arrived."),
                    void 0 === B.config.globalProperties.cy &&
                      ((B.config.globalProperties.cy = p()),
                      p().use(z()),
                      p().use(J()),
                      p().use(A())),
                    0 === Object.keys(B._context.provides).length &&
                      B.provide("taxonomyDataMessage", t),
                    null === B._instance && B.mount("#app");
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
          var r = 1 / 0;
          for (l = 0; l < e.length; l++) {
            (n = e[l][0]), (a = e[l][1]), (s = e[l][2]);
            for (var d = !0, i = 0; i < n.length; i++)
              (!1 & s || r >= s) &&
              Object.keys(o.O).every(function (e) {
                return o.O[e](n[i]);
              })
                ? n.splice(i--, 1)
                : ((d = !1), s < r && (r = s));
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
            r = n[0],
            d = n[1],
            i = n[2],
            c = 0;
          if (
            r.some(function (t) {
              return 0 !== e[t];
            })
          ) {
            for (a in d) o.o(d, a) && (o.m[a] = d[a]);
            if (i) var l = i(o);
          }
          for (t && t(n); c < r.length; c++)
            (s = r[c]), o.o(e, s) && e[s] && e[s][0](), (e[s] = 0);
          return o.O(l);
        },
        n = (self["webpackChunkcls_cytoscape"] =
          self["webpackChunkcls_cytoscape"] || []);
      n.forEach(t.bind(null, 0)), (n.push = t.bind(null, n.push.bind(n)));
    })();
  var n = o.O(void 0, [998], function () {
    return o(3214);
  });
  n = o.O(n);
})();
//# sourceMappingURL=app.724f54b1.js.map
