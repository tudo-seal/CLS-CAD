(function () {
  "use strict";
  var e = {
      7452: function (e, t, o) {
        var n = o(9242),
          a = o(3396);
        function s(e, t, o, n, s, i) {
          const c = (0, a.up)("GraphWrapper");
          return (0, a.wg)(), (0, a.j4)(c);
        }
        function i(e, t, o, n, s, i) {
          const c = (0, a.up)("GraphContent");
          return (0, a.wg)(), (0, a.j4)(c);
        }
        const c = (e) => (
            (0, a.dD)("data-v-245bbc73"), (e = e()), (0, a.Cn)(), e
          ),
          r = { id: "container", class: "h-screen" },
          l = {
            id: "nav-bar-top",
            class: "flex flex-row justify-between items-center h-8",
          },
          d = c(() =>
            (0, a._)(
              "div",
              null,
              "Headline Wrapper (only for debugging purpose)",
              -1
            )
          ),
          m = c(() => (0, a._)("div", { id: "cy" }, null, -1));
        function h(e, t, o, n, s, i) {
          const c = (0, a.up)("PopupWindow");
          return (
            (0, a.wg)(),
            (0, a.iD)("div", r, [
              (0, a._)("div", l, [
                d,
                (0, a._)(
                  "button",
                  {
                    class: "bg-blue-500 hover:bg-lime-600 px-6 h-full",
                    onClick: t[0] || (t[0] = (...e) => i.save && i.save(...e)),
                  },
                  "Save"
                ),
              ]),
              m,
              s.windowEnabled
                ? ((0, a.wg)(),
                  (0, a.j4)(
                    c,
                    {
                      key: 0,
                      action: s.action,
                      "element-name": s.currentElement,
                      x: s.positionX,
                      y: s.positionY,
                      onCancel: i.closeWindow,
                      onAction: i.actionWindow,
                    },
                    null,
                    8,
                    ["action", "element-name", "x", "y", "onCancel", "onAction"]
                  ))
                : (0, a.kq)("", !0),
            ])
          );
        }
        o(7658);
        var u = o(7139);
        const g = { class: "flex flex-row place-content-between bg-gray-400" };
        function p(e, t, o, s, i, c) {
          return (
            (0, a.wg)(),
            (0, a.iD)(
              "div",
              {
                class: "w-100 bg-amber-400 p-1",
                style: (0, u.j5)(c.cssWindow),
              },
              [
                (0, a._)(
                  "div",
                  null,
                  (0, u.zw)(o.action) + " " + (0, u.zw)(o.elementName),
                  1
                ),
                (0, a.wy)(
                  (0, a._)(
                    "input",
                    {
                      class: "w-100",
                      ref: "focusMe",
                      "onUpdate:modelValue":
                        t[0] || (t[0] = (e) => (i.newName = e)),
                      onKeydown:
                        t[1] ||
                        (t[1] = (0, n.D2)((e) => c.doAction(), ["enter"])),
                    },
                    null,
                    544
                  ),
                  [[n.nr, i.newName]]
                ),
                (0, a._)("div", g, [
                  (0, a._)(
                    "button",
                    {
                      class: "ml-2",
                      onClick:
                        t[2] ||
                        (t[2] = (...e) => c.closeWindow && c.closeWindow(...e)),
                    },
                    "Cancel"
                  ),
                  (0, a._)(
                    "button",
                    {
                      class: "mr-2",
                      onClick: t[3] || (t[3] = (e) => c.doAction()),
                    },
                    (0, u.zw)(o.action),
                    1
                  ),
                ]),
              ],
              4
            )
          );
        }
        var y = {
            name: "PopupWindow",
            props: {
              action: void 0,
              elementName: void 0,
              x: Number,
              y: Number,
            },
            data() {
              return { newName: "" };
            },
            mounted() {
              this.$refs.focusMe.focus();
            },
            computed: {
              cssWindow() {
                return {
                  position: "absolute",
                  left: this.x + -50 + "px",
                  top: this.y + 150 + "px",
                  "z-index": "1000",
                };
              },
            },
            methods: {
              closeWindow: function () {
                this.$emit("cancel");
              },
              doAction: function () {
                "" !== this.newName &&
                  this.$emit("action", {
                    action: this.action,
                    elementName: this.elementName,
                    newName: this.newName,
                  });
              },
            },
          },
          f = o(89);
        const w = (0, f.Z)(y, [["render", p]]);
        var v = w,
          N = o(2584),
          b = o.n(N);
        class x {
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
        var E = new x();
        function D(e, t, o) {
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
        let M, C;
        class k {
          static drawEdge(e, t, o, n, a) {
            console.log(n);
            const s = o.$("node[name='" + e + "']");
            n.enableDrawMode(),
              n.start(s),
              o.on("cxttap", () => {
                n.drawMode && (n.disableDrawMode(), n.stop());
              }),
              o.on("ehhoverover", (e, t, n) => {
                let s = D(t.data().name, n.data().name, a);
                s
                  ? (console.log("circle found"), E.color(o, "red"), (M = !1))
                  : (console.log("green arrow"), E.color(o, "green"), (M = !0));
              }),
              o.on("ehhoverout", () => {
                E.color(o, "purple");
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
                  M
                    ? (a[n.id()].push(s.id()),
                      o
                        .$(
                          "edge[source='" +
                            n.data().name +
                            "'][target='" +
                            s.data().name +
                            "']"
                        )
                        .data(
                          "name",
                          i.source().data().name + "->" + i.target().data().name
                        ))
                    : (console.log("remove invalid edge"),
                      o.remove(
                        "edge[source='" +
                          n.data().name +
                          "'][target='" +
                          s.data().name +
                          "']"
                      ),
                      t && this.recoverEdge(o, a)),
                  console.table(a);
              }),
              o.on("ehcancel", () => {
                console.log("cancelled"), t && this.recoverEdge(o, a);
              }),
              o.on("ehstop", () => {
                console.log("stopped."),
                  (t = !1),
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
            C = e;
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
            const o = e.edges("[source='" + t + "']");
            return o;
          }
          static getTargetEdges(e, t) {
            const o = e.edges("[target='" + t + "']");
            return o;
          }
          static removeEdge(e, t, o) {
            let n = t.source().data().name,
              a = t.target().data().name;
            o[n].splice(o[n].indexOf(a), 1),
              e.remove("edge[name='" + t.data().name + "']");
          }
          static recoverEdge(e, t) {
            e.add({
              group: "edges",
              data: {
                source: C.source().data().name,
                target: C.target().data().name,
                name: C.source().data().name + "->" + C.target().data().name,
              },
            }),
              t[C.source().data().name].push(C.target().data().name);
          }
        }
        var O = k;
        let j = {
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
        var $ = JSON.parse(
            '[{"selector":".node","style":{"label":"data(name)","text-valign":"center","color":"#000000","background-color":"#639a00","font-family":"Courier, monospace","font-weight":"600"}},{"selector":".highlightNode","style":{"label":"data(name)","text-valign":"center","background-color":"#dc2626","font-family":"Courier, monospace","font-weight":"600"}},{"selector":"edge","style":{"width":4,"target-arrow-shape":"triangle","line-color":"#706a6a","target-arrow-color":"#222222","curve-style":"bezier"}},{"selector":".eh-source","style":{"border-width":2}},{"selector":".eh-target","style":{"border-width":2}},{"selector":".eh-preview, .eh-ghost-edge","style":{"line-color":"purple"}}]'
          ),
          S = {
            name: "GraphContent",
            inject: ["taxonomyDataMessage"],
            components: { PopupWindow: v },
            data() {
              return {
                cyNodes: [],
                cyEdges: [],
                taxonomyString: this.taxonomyDataMessage,
                taxonomyData: void 0,
                taxonomyID: void 0,
                eh: void 0,
                nodeMenu: void 0,
                edgeMenu: void 0,
                coreMenu: void 0,
                renameMenu: void 0,
                windowEnabled: !1,
                action: void 0,
                currentElement: void 0,
                positionX: void 0,
                positionY: void 0,
                oldNode: void 0,
              };
            },
            mounted() {
              this.setTaxonomyData();
            },
            methods: {
              setTaxonomyData: function () {
                (this.taxonomyData = JSON.parse(this.taxonomyString)),
                  (this.taxonomyID = this.taxonomyData.ID);
                for (let [e, t] of Object.entries(this.taxonomyData))
                  this.cyNodes.push({ data: { id: e, name: e } }),
                    t.forEach((t) => {
                      this.cyEdges.push({
                        data: { source: e, target: t, name: e + "->" + t },
                      });
                    });
                (this.cy = b()({
                  container: document.getElementById("cy"),
                  layout: { name: "dagre", fit: !0, spacingFactor: 1 },
                  style: $,
                  elements: { nodes: this.cyNodes, edges: this.cyEdges },
                })),
                  this.cy.nodes().addClass("node"),
                  this.initNodeMenu(),
                  this.initEdgeMenu(),
                  this.initCoreMenu(),
                  (this.eh = this.cy.edgehandles(j));
              },
              initNodeMenu: function () {
                this.nodeMenu = this.cy.cxtmenu({
                  menuRadius: 75,
                  selector: ".node",
                  commands: [
                    {
                      fillColor: "rgba(200, 200, 200, 0.75)",
                      content: "draw edge",
                      contentStyle: { color: "black" },
                      select: (e) => {
                        this.drawEdge(e.data().name, !1);
                      },
                    },
                    {
                      fillColor: "rgba(200, 200, 200, 0.75)",
                      content: "rename",
                      contentStyle: { color: "black" },
                      select: (e) => {
                        this.renameNode(e.data().name, e.position(), "Rename");
                      },
                    },
                    {
                      fillColor: "rgb(191,38,38)",
                      content: "delete",
                      contentStyle: { color: "black" },
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
                      fillColor: "rgb(191,38,38)",
                      content: "delete",
                      contentStyle: { color: "black" },
                      select: (e) => {
                        console.log("deleteEdge"),
                          O.removeEdge(this.cy, e, this.taxonomyData);
                      },
                    },
                    {
                      fillColor: "rgb(92,125,204)",
                      content: "rearrange",
                      contentStyle: { color: "black" },
                      select: (e) => {
                        O.initTmpEdge(e),
                          O.removeEdge(this.cy, e, this.taxonomyData);
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
                      fillColor: "rgb(82,190,39)",
                      content: "add node",
                      contentStyle: { color: "black" },
                      select: (e, t) => {
                        this.createNode(t);
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
                      fillColor: "rgb(191,38,38)",
                      content: "rename",
                      contentStyle: { color: "black" },
                      select: (e) => {
                        console.log("rename", e),
                          this.renameNode(
                            e.data().name,
                            e.position(),
                            "Rename+"
                          );
                      },
                    },
                    {
                      fillColor: "rgb(92,125,204)",
                      content: "merge",
                      contentStyle: { color: "black" },
                      select: (e) => {
                        console.log("merge", e), this.mergeNodes(e.data().name);
                      },
                    },
                  ],
                  openMenuEvents: "cxttapstart taphold",
                });
              },
              drawEdge: function (e, t) {
                O.drawEdge(e, t, this.cy, this.eh, this.taxonomyData);
              },
              renameNode: function (e, t, o) {
                console.log("starting rename procedure at ", t),
                  console.log("x = ", t.x),
                  this.cy.panningEnabled(!1),
                  (this.action = o),
                  (this.currentElement = e),
                  (this.positionX = t.x),
                  (this.positionY = t.y),
                  (this.windowEnabled = !0);
              },
              createNode: function (e) {
                this.cy.panningEnabled(!1),
                  (this.action = "Create Node"),
                  (this.currentElement = ""),
                  (this.positionX = e.position.x),
                  (this.positionY = e.position.y),
                  (this.windowEnabled = !0);
              },
              removeNode: function (e) {
                const t = O.getAllEdges(this.cy, e);
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
                  this.cy.remove("node[name='" + e + "']"),
                  delete this.taxonomyData[e];
              },
              mergeNodes: function (e, t) {
                if (void 0 !== this.taxonomyData[e]) {
                  const o = "(" + e + ")",
                    n = this.cy.$("node[name='" + o + "']");
                  this.taxonomyData[this.oldNode].forEach((t) => {
                    this.taxonomyData[e].push(t);
                  }),
                    delete this.taxonomyData[this.oldNode];
                  const a = O.getTargetEdges(this.cy, n.id());
                  console.log("name: ", n.id()),
                    a.length > 0 &&
                      a.forEach((e) => {
                        let t = e.source().data().name;
                        this.taxonomyData[t].splice(
                          this.taxonomyData[t].indexOf(this.oldNode),
                          1
                        );
                      }),
                    void 0 !== t && (e = t);
                  const s = O.getSourceEdges(this.cy, n.id());
                  s.length > 0 &&
                    s.forEach((t) => {
                      console.log(e, "->", t.target().data().name),
                        this.cy.add({
                          group: "edges",
                          data: {
                            source: e,
                            target: t.target().data().name,
                            name: e + "->" + t.target().data().name,
                          },
                        });
                    }),
                    this.removeNode(o);
                  const i = o.slice(1, o.length - 1);
                  this.cy.$("node[name='" + i + "']").classes("node"),
                    this.renameMenu.destroy(),
                    this.nodeMenu.destroy(),
                    this.initNodeMenu(),
                    console.table(this.taxonomyData);
                } else {
                  console.log("CASE 2: swap nodes");
                  const t = e.slice(1, e.length - 1),
                    o = this.cy.$("node[name='" + e + "']"),
                    n = this.cy.$("node[name='" + t + "']");
                  o.json({ data: { name: t } }),
                    n.json({ data: { name: e } }),
                    this.mergeNodes(t, this.oldNode);
                }
                this.oldNode = void 0;
              },
              closeWindow: function () {
                console.log("cancel"),
                  (this.windowEnabled = !1),
                  this.cy.panningEnabled(!0);
              },
              actionWindow: function (e) {
                switch ((console.log(e), e.action)) {
                  case "Rename":
                    void 0 !== this.taxonomyData[e.newName]
                      ? (this.nodeMenu.destroy(),
                        this.cy
                          .$("node[name='" + e.elementName + "']")
                          .classes("highlightNode"),
                        this.cy
                          .$("node[name='" + e.newName + "']")
                          .classes("highlightNode"),
                        this.initNodeMenu(),
                        this.initRenameMenu(),
                        (this.oldNode = e.elementName),
                        this.cy
                          .$("[name='" + e.elementName + "']")
                          .json({ data: { name: "(" + e.newName + ")" } }))
                      : (console.log(
                          "renaming ",
                          e.elementName,
                          " to ",
                          e.newName
                        ),
                        (this.taxonomyData[e.newName] = []),
                        this.addEdges(
                          e.elementName,
                          e.newName,
                          this.taxonomyData
                        ),
                        delete this.taxonomyData[e.elementName],
                        this.cy
                          .$("[name='" + e.elementName + "']")
                          .json({ data: { name: e.newName } }),
                        console.table(this.taxonomyData));
                    break;
                  case "Rename+":
                    if (
                      (console.log("entered!"), e.elementName.startsWith("("))
                    ) {
                      console.log("renaming ", this.oldNode, " to ", e.newName);
                      let t = e.elementName.slice(1, e.elementName.length - 1);
                      void 0 !== this.taxonomyData[e.newName]
                        ? alert(
                            e.newName +
                              " is already in scope(it may be a ghost copy of cytoscape)"
                          )
                        : ((this.taxonomyData[e.newName] = []),
                          this.addEdges(
                            e.elementName,
                            e.newName,
                            this.taxonomyData
                          ),
                          delete this.taxonomyData[this.oldNode],
                          this.cy
                            .$("[name='" + e.elementName + "']")
                            .json({ data: { name: e.newName } }),
                          (this.oldNode = void 0),
                          this.renameMenu.destroy(),
                          this.nodeMenu.destroy(),
                          this.cy.$("node[name='" + t + "']").classes("node"),
                          this.cy
                            .$("node[name='" + e.newName + "']")
                            .classes("node"),
                          this.initNodeMenu());
                    } else
                      console.log("old node:", this.oldNode),
                        console.log(
                          "renaming ",
                          e.elementName,
                          " to ",
                          e.newName
                        ),
                        void 0 !== this.taxonomyData[e.newName]
                          ? alert(
                              e.newName +
                                " is already in scope(it may be a ghost copy of cytoscape)"
                            )
                          : ((this.oldNode = void 0),
                            this.actionWindow({
                              action: "Rename",
                              elementName: e.elementName,
                              newName: e.newName,
                            }),
                            this.actionWindow({
                              action: "Rename+",
                              elementName: "(" + e.elementName + ")",
                              newName: e.elementName,
                            }));
                    break;
                  case "Create Node":
                    this.cy.add({ data: { id: e.newName, name: e.newName } }),
                      this.cy
                        .$("node[name='" + e.newName + "']")
                        .addClass("node"),
                      (this.taxonomyData[e.newName] = []);
                    break;
                }
                (this.windowEnabled = !1), this.cy.panningEnabled(!0);
              },
              addEdges: function (e, t, o) {
                const n = this.cy.$("node[name='" + e + "']").connectedEdges();
                n.forEach((n) => {
                  let a = n.source().data().name,
                    s = n.target().data().name;
                  if (s === e)
                    if (
                      (console.log("parent found (", a, ")"),
                      void 0 !== this.oldNode)
                    ) {
                      let e = o[a].indexOf(this.oldNode);
                      o[a][e] = t;
                    } else {
                      let n = o[a].indexOf(e);
                      o[a][n] = t;
                    }
                  else console.log("child found (", s, ")"), o[t].push(s);
                });
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
          };
        const W = (0, f.Z)(S, [
          ["render", h],
          ["__scopeId", "data-v-245bbc73"],
        ]);
        var _ = W,
          R = { name: "GraphWrapper", components: { GraphContent: _ } };
        const T = (0, f.Z)(R, [["render", i]]);
        var A = T,
          I = { name: "App", components: { GraphWrapper: A } };
        const G = (0, f.Z)(I, [["render", s]]);
        var P = G,
          z = o(9253),
          J = o.n(z),
          X = o(1454),
          Y = o.n(X),
          Z = o(1590),
          F = o.n(Z);
        const q = (0, n.ri)(P);
        window.fusionJavaScriptHandler = {
          handle: function (e, t) {
            try {
              if ("updateMessage" === e) console.log("updated");
              else if ("taxonomyDataMessage" === e)
                console.log("TaxonomyData arrived."),
                  void 0 === q.config.globalProperties.cy &&
                    ((q.config.globalProperties.cy = b()),
                    b().use(J()),
                    b().use(Y()),
                    b().use(F())),
                  0 === Object.keys(q._context.provides).length &&
                    q.provide("taxonomyDataMessage", t),
                  null === q._instance && q.mount("#app");
              else if ("taxonomyIDMessage" === e)
                console.log("taxonomyIDMessage arrived."), (document.title = t);
              else {
                if ("debugger" !== e)
                  return (
                    console.log("testelse"), `Unexpected command type: ${e}`
                  );
                console.log("testdebugger");
              }
            } catch (o) {
              console.log(o),
                console.log(`Exception caught with command: ${e}, data: ${t}`);
            }
            return "OK";
          },
        };
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
          for (d = 0; d < e.length; d++) {
            (n = e[d][0]), (a = e[d][1]), (s = e[d][2]);
            for (var c = !0, r = 0; r < n.length; r++)
              (!1 & s || i >= s) &&
              Object.keys(o.O).every(function (e) {
                return o.O[e](n[r]);
              })
                ? n.splice(r--, 1)
                : ((c = !1), s < i && (i = s));
            if (c) {
              e.splice(d--, 1);
              var l = a();
              void 0 !== l && (t = l);
            }
          }
          return t;
        }
        s = s || 0;
        for (var d = e.length; d > 0 && e[d - 1][2] > s; d--) e[d] = e[d - 1];
        e[d] = [n, a, s];
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
            c = n[1],
            r = n[2],
            l = 0;
          if (
            i.some(function (t) {
              return 0 !== e[t];
            })
          ) {
            for (a in c) o.o(c, a) && (o.m[a] = c[a]);
            if (r) var d = r(o);
          }
          for (t && t(n); l < i.length; l++)
            (s = i[l]), o.o(e, s) && e[s] && e[s][0](), (e[s] = 0);
          return o.O(d);
        },
        n = (self["webpackChunkcls_cytoscape"] =
          self["webpackChunkcls_cytoscape"] || []);
      n.forEach(t.bind(null, 0)), (n.push = t.bind(null, n.push.bind(n)));
    })();
  var n = o.O(void 0, [998], function () {
    return o(7452);
  });
  n = o.O(n);
})();
//# sourceMappingURL=app.641dfe98.js.map
