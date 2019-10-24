

    var idToNode = {};
    var nodeList = [];
    var edgeList = [];
    var disconnected = [];


    $json.nodes.forEach(function (n) {
        idToNode[n.id] = n;
        nodeList.push(n.name);
    });

    $json.links.forEach(function (e) {
        e.source = idToNode[e.source].name;
        e.target = idToNode[e.target].name;
        edgeList.push([e.source, e.target]);
    });


    $json["disconnected nodes"].forEach(function (n) {
        disconnected.push(n);
    });



    var G = new jsnx.DiGraph();


    //G.addNodesFrom(nodeList, {color: '#7FFFD4'});
    //G.addEdgesFrom(edgeList, {color: '#FFA07A'});



    // Add nodes with different colors
    nodeList.forEach(function (n) {
        if (disconnected.includes(n)) {
            G.addNodesFrom([[n, {color: '#f4f5ff'}]]);
        }
        else {
            G.addNodesFrom([[n, {color: '#7FFFD4'}]]);//'#FFB3D4'
        }
    });


    // Add edges with different colors
    $json.links.forEach(function (e) {
        if (e.is_transitive) {
            G.addEdgesFrom([[e.source, e.target, {color: '#911aff'}]]);
        }
        else if (e.has_mutual){
            G.addEdgesFrom([[e.source, e.target, {color: '#FF0000'}]]);
        }
        else {
            G.addEdgesFrom([[e.source, e.target, {color: '#FFA07A'}]]);
        }
    });



    // Draw the graph
    jsnx.draw(G, {
        element: '#canvas',
        layoutAttr: {
            'charge': -120,
            'linkDistance': 40
        },
        withLabels: true,
        nodeStyle: {
            fill: function (d) {
                return d.data.color;
            }
        },
        edgeStyle: {
            'stroke-width': 4,
            fill: function (d) {
                return d.data.color;
            }
        },
        labelStyle: {
            "font-size": '10px',
            "font-family": "sans-serif",
            'text-anchor': 'outside',
            fill: 'black'
        },
        stickyDrag: true
    }, true);


