var margin = {top: 360, right: 10, left: 440},
    width = 1500,
    height = 1500;

var svg = d3.select("div.container").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top);
    //width = +svg.attr("width"),
    //height = +svg.attr("height");



var color = d3.scaleOrdinal(d3.schemeCategory20);

var simulation = d3.forceSimulation()
    .force("link", d3.forceLink().distance(10).strength(0.5))
    .force("charge", d3.forceManyBody())
    .force("center", d3.forceCenter(width / 2, height / 2));

    
    var annotators = new Set();

    svg.append("svg:defs").append("svg:marker")
        .attr("id", "arrow")
        .attr("viewBox", "0 -5 10 10")
        .attr('refX', -20)//so that it comes towards the center.
        .attr("markerWidth", 3)
        .attr("markerHeight", 3)
        .attr("orient", "auto")
        .append("svg:path")
        .attr("d", "M0,-5L10,0L0,5");

    var nodes = $json.nodes,
        nodeById = d3.map(nodes, function(d) { return d.id; }),
        links = $json.links,
        bilinks = [];

    links.forEach(function(link) {
        var s = link.source = nodeById.get(link.source),
            t = link.target = nodeById.get(link.target),
            i = {}; // intermediate node
        nodes.push(i);
        links.push({source: s, target: i}, {source: i, target: t});
        bilinks.push([s, i, t]);
        for (var a=0; a<link.annotators.length; a++) {
            if (!annotators.has(link.annotators[a])) {
                annotators.add(link.annotators[a]);
                //populate the list of the Annotator filter
                //document.getElementById('annotator-select').innerHTML += '<option value="' + link.annotators[a] + '">' + link.annotators[a] + '</option>';
            }
        } 
        
    });
    
    Array.from($json.annotator).forEach(function(ann){
            //annotators.add(ann)
            document.getElementById('annotator-select').innerHTML += '<option value="' + ann + '">' + ann + '</option>';
        })


    var link = svg.selectAll(".link")
        .data(bilinks)
        .enter().append("path")
        //.attr("id", "path: "+ links.source.name + " --> "+ links.target.name)
        .attr('id', function (d) { return 'path: ' + d[0].name + ' --> ' + d[2].name; })
        .attr("class", "link")
        .attr('marker-start', (d) => "url(#arrow)");//attach the arrow from defs

    var node = svg.selectAll(".node")
        .data(nodes.filter(function(d) { return d.id; }))
        .enter().append("circle")
        .attr("class", "node")
        .attr("r", 5)
        .attr("fill", function(d) { return color(d.cluster); })
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    node.append("title")
        .text(function(d) { return d.name; });

    simulation
        .nodes(nodes)
        .on("tick", ticked);

    simulation.force("link")
        .links(links);

    function ticked() {
        link.attr("d", positionLink);
        node.attr("transform", positionNode);
        //link.attr( "d", (d) => "M" + d.source.x + "," + d.source.y + ", " + d.target.x + "," + d.target.y);
        //link.attr( "d", (d) => "M" + d[0].x + "," + d[0].y + ", " + d[2].x + "," + d[2].y);
        link.attr( "d", (d) => positionLink(d));
    }



    /**
     * Annotator filer
     */
    d3.select('#annotator-select')
        .on('click', function () {
            var selection = this.value;
            //FIXME: is 'all' is selected show all sections!!!
            if (selection === "All") {
                var l = document.getElementsByClassName('link');
                console.log(l);
                for (var x of l) {
                    //console.log(x);
                    document.getElementById(x.id).style.display = 'block';
                }
            }
            $json.links.forEach(function (e) {
                //console.log(e);
                if (e.annotators) {
                    if (e.annotators.includes(selection)) {
                        document.getElementById('path: '+ e.source.name +' --> '+ e.target.name).style.display = 'block';
                    }
                    else {
                        document.getElementById('path: '+ e.source.name +' --> '+ e.target.name).style.display = 'none';
                    }
                }
            });
        });



function positionLink(d) {
    return "M" + d[0].x + "," + d[0].y
        + "S" + d[1].x + "," + d[1].y
        + " " + d[2].x + "," + d[2].y;
}

function positionNode(d) {
    return "translate(" + d.x + "," + d.y + ")";
}

function dragstarted(d) {
    if (!d3.event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(d) {
    d.fx = d3.event.x;
    d.fy = d3.event.y;
}

function dragended(d) {
    if (!d3.event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}



