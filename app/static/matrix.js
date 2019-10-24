
// Set global dimensions
var margin = {top: 360, right: 10, left: 440},
    width = 1500,
    height = 1500;


var x = d3.scale.ordinal().rangeBands([0, width]),
    z = d3.scale.linear().domain([0, 4]).clamp(true),
    c = d3.scale.category10().domain(d3.range(10));

// Add a svg
var svg = d3.select("div.container").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top)
    /*.style("margin-left", margin.left + "px") */
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

// Import json, initialize the matrix, retrieve labels and dimensions


    var matrix = [],
        nodes = $json.nodes;
        n = nodes.length;

    // Compute index of each node
    nodes.forEach(function(node, i) {
        node.index = i;
        node.count = 0;
        matrix[i] = d3.range(n).map(function(j) { return {x: j, y: i, z: 0}; });
    });

    // Convert links to matrix and count annotators' positive judgements
    $json.links.forEach(function(link) {
        if (matrix[link.source]) {
        matrix[link.source][link.target].z += link.annotators.length;
        nodes[link.source].count += link.annotators.length;
        nodes[link.target].count += link.annotators.length;
        }
    });

    // Compute the different orders
    var orders = {
        name: d3.range(n).sort(function(a, b) { return d3.ascending(nodes[a].name, nodes[b].name); }),
        frequency: d3.range(n).sort(function(a, b) { return nodes[b].count - nodes[a].count; }),
        cluster: d3.range(n).sort(function(a, b) { return nodes[b].cluster - nodes[a].cluster; }),
        temporal: d3.range(n).sort(function(a, b) { return nodes[a].id - nodes[b].id; }),
        //TODO: add ordering by number of co-occurrances in the same section
        // co_occurrance: d3.range(n).sort(function(a, b) { return nodes[a].sections - nodes[b].sections; });
        annotators: d3.range(n).sort(function(a, b) { return } )
    };

    // Set the default sorting (by name)
    x.domain(orders.name);

    svg.append("rect")
        .attr("class", "background")
        .attr("width", width)
        .attr("height", height);

    var row = svg.selectAll(".row")
        .data(matrix)
        .enter().append("g")
        .attr("class", "row")
        .attr("transform", function(d, i) { return "translate(0," + x(i) + ")"; })
        .each(row);

    row.append("line")
        .attr("x2", width);

    row.append("text")
        .attr("x", -6)
        .attr("y", x.rangeBand() / 2)
        .attr("dy", ".32em")
        .attr("text-anchor", "end")
        .text(function(d, i) { return nodes[i].name; });

    var column = svg.selectAll(".column")
        .data(matrix)
        .enter().append("g")
        .attr("class", "column")
        .attr("transform", function(d, i) { return "translate(" + x(i) + ")rotate(-90)"; });

    column.append("line")
        .attr("x1", -width);

    column.append("text")
        .attr("x", 6)
        .attr("y", x.rangeBand() / 2)
        .attr("dy", ".32em")
        .attr("text-anchor", "start")
        .text(function(d, i) { return nodes[i].name; });

    function row(row) {
        var cell = d3.select(this).selectAll(".cell")
            .data(row.filter(function(d) { return d.z; }))
            .enter().append("rect")
            .attr("class", "cell")
            .attr("x", function(d) { return x(d.x); })
            .attr("width", x.rangeBand())
            .attr("height", x.rangeBand())
            .style("fill-opacity", function(d) { return z(d.z); })
            .style("fill", function(d) { return nodes[d.x].cluster == nodes[d.y].cluster ? c(nodes[d.x].cluster) : null; })
            .on("mouseover", mouseover)
            .on("mouseout", mouseout)
            .append('title').text(function (d) { return nodes[d.y].name + ' ---> ' + nodes[d.x].name;});
    }

    function mouseover(p) {
        d3.selectAll(".row text").classed("active", function(d, i) { return i == p.y; });
        d3.selectAll(".column text").classed("active", function(d, i) { return i == p.x; });
    }


    function mouseout() {
        d3.selectAll("text").classed("active", false);
        //document.getElementById("popup").style.display = 'none';
    }

    d3.select("#order").on("change", function() {
        clearTimeout(timeout);
        order(this.value);
    });

    function order(value) {
        x.domain(orders[value]);

        var t = svg.transition().duration(60);

        t.selectAll(".row")
            .delay(function(d, i) { return x(i) * 4; })
            .attr("transform", function(d, i) { return "translate(0," + x(i) + ")"; })
            .selectAll(".cell")
            .delay(function(d) { return x(d.x) * 4; })
            .attr("x", function(d) { return x(d.x); });

        t.selectAll(".column")
            .delay(function(d, i) { return x(i) * 4; })
            .attr("transform", function(d, i) { return "translate(" + x(i) + ")rotate(-90)"; });
    }

    var timeout = setTimeout(function() {
        order("group");
        d3.select("#order").property("selectedIndex", 2).node().focus();
    }, 5000);
