var concepts = [];
var insertedRelations = [];
var weights = [];
var sent_ids = [];
var clickedResult = {};


    var result = JSON.parse($json);
        //console.log(result);

    insertedRelations = result["savedInsertedRelations"];

    if(insertedRelations) {
        for (let rel of insertedRelations) {
            if (!concepts.includes(rel["prerequisite"])) {
                concepts.push(rel["prerequisite"]);
            }
            if (!concepts.includes(rel["advanced"])) {
                concepts.push(rel["advanced"]);
            }
            //let currSent = $sentList[rel["sent"]-1]["text"];
            //console.log(insertedRelations.indexOf(rel));
            //console.log(currSent);
        }
    }

    if(insertedRelations) {
        weights = Array.from(new Set(insertedRelations.map(x => x["weight"])));
    
    }
    
    sent_ids = $sentList.map(x => x.sent_id);

        //populate the select inputs with options

    var options = "<option value='ANY CONCEPT'>ANY CONCEPT</option>";
    for(let i = 0; i < concepts.length; i++) {
        options += "<option value='" + concepts[i] + "'>" + concepts[i] + "</option>";
    }
    $('select[name="prerequisite_name"]').append(options);

    options = "<option value='ANY CONCEPT'>ANY CONCEPT</option>";
    for(let i = 0; i < concepts.length; i++) {
        options += "<option value='" + concepts[i] + "'>" + concepts[i] + "</option>";
    }
    $('select[name="advanced_name"]').append(options);

    options = "<option value='ANY WEIGHT'>ANY WEIGHT</option>";
    for(let i = 0; i < weights.length; i++) {
        options += "<option value='" + weights[i] + "'>" + weights[i] + "</option>";
    }
    $('select[name="edge_weight"]').append(options);

    options = "<option value='ANY SENTENCE'>ANY SENTENCE</option>";
    for(let i = 0; i < sent_ids.length; i++) {
        options += "<option value='" + sent_ids[i] + "'>" + sent_ids[i] + "</option>";
    }
    $('select[name="sent_id"]').append(options);
 


$("#find").click(function () {
    //erase the paper from previous results and re-populate it
    //$('#paper').html("");
    $('#paper').empty();

    let selectedSentence = $('#sent_id').val();
    let selectedPrereq = $('#prerequisite_name').val();
    let selectedAdvanced = $('#advanced_name').val();
    let selectedWeight = $('#edge_weight').val();

    for (let rel of insertedRelations) {
        if ((selectedPrereq === "ANY CONCEPT" || rel['prerequisite'] === selectedPrereq) &&
            (selectedAdvanced === "ANY CONCEPT" || rel['advanced'] === selectedAdvanced) &&
            (selectedWeight === "ANY WEIGHT" || rel['weight'] === selectedWeight) &&
            (selectedSentence === "ANY SENTENCE" || rel['sent'] === selectedSentence)) {

            //append a text area for each relation
            let currSent = $sentList[rel["sent"]-1]["text"];
            console.log("currSent: ", currSent);
            console.log("index of curr rel: ", insertedRelations.indexOf(rel));

            $("#paper").append('<div class="result_margin">Context: \n' +
                '                       <input id="title' + insertedRelations.indexOf(rel) + '" type="text" name="title" readonly />\n' +
                '                   </div>\n' +
                '                   <textarea class="result_text" style="width:-webkit-fill-available" name="text" rows="4" readonly '+
                '                       id="text' + insertedRelations.indexOf(rel) + '"'+
                '                       rel_id="' + insertedRelations.indexOf(rel) + '"'+
                '                       sent_id="' + rel['sent'] + '"'+
                '                       prereq="' + rel['prerequisite'] + '"'+
                '                       advanced="' + rel['advanced'] + '"'+
                '                       weight="' + rel['weight'] + '"'+
                '                   >'+ currSent +
                '                   </textarea>\n' +
                '                   <br />');
                //'                  <textarea class="result_text" id="text' + insertedRelations.indexOf(rel) + '" name="text" rows="4" readonly style="overflow: hidden; word-wrap: break-word; resize: none; height: 160px; ">'+ currSent +'</textarea>');
        }
    }

    $('.result_text').click(function (e) {
        clickedResult = {
            rel_id: e.target.getAttribute("rel_id"),
            sent_id: e.target.getAttribute("sent_id"),
            prereq: e.target.getAttribute("prereq"),
            advanced: e.target.getAttribute("advanced"),
            weight: e.target.getAttribute("weight")
        };
        console.log(clickedResult);
        $('#modalAnalysis').modal('show');
    });

    $('#modalAnalysis').on('show.bs.modal', function(e) {

        $('#minigraph_modal').html($('#minigraph').html());

        let centralSent = $sentList[clickedResult.sent_id-1]["text"];

        //erase the paper from previous results and re-populate it
        $('#paper_modal').empty();
        $("#paper_modal").append('<textarea class="result_text_modal" style="width:-webkit-fill-available" rows="7" name="text" readonly '+
            '                       id="text' + clickedResult.rel_id + '"'+ '>'+ centralSent +
            '                     </textarea>');

        // populate the table in POS tab
        $("#table_pos").find("tr:not(:first)").remove();
        let tokens = $conll.filter(x => x.sent_id.toString() === clickedResult.sent_id);
        for (let tok of tokens) {
            //FIXME: highlighted_text += tok["forma"] + " ";
            let table = document.getElementById("table_pos");
            let row = table.insertRow(table.rows.length);
            let cell0 = row.insertCell(0);
            let cell1 = row.insertCell(1);
            let cell2 = row.insertCell(2);
            let cell3 = row.insertCell(3);
            let cell4 = row.insertCell(4);
            let cell5 = row.insertCell(5);
            cell0.innerHTML = tok["sent_id"];
            cell1.innerHTML = tok["tok_id"];
            cell2.innerHTML = tok["forma"];
            cell3.innerHTML = tok["lemma"];
            cell4.innerHTML = tok["pos_coarse"];
            cell5.innerHTML = tok["pos_fine"];
        }

        /*
        //highlight the concepts
        var highlighted_text = "";
        for (let )
        for (let tok of tokens) {
            highlighted_text += tok["forma"] + " ";
        */
        //find word formas to highlight
        //$conll.filter(x => x.sent_id === clickedResult.sent_id).filter(x => x["lemma"].toUpperCase() === "COMPUTER")

        $('#prev_button').click(function () {
            console.log("clicked prev button");
            let prevSent = $sentList[clickedResult.sent_id - 2]["text"];
            $('#paper_modal').empty();
            $("#paper_modal").append('<textarea class="result_text_modal" name="text" readonly '+
                '                       id="text' + clickedResult.rel_id + '"'+ '>'+ prevSent +
                '                     </textarea>');
        });

        $('#next_button').click(function () {
            console.log("clicked next button");
            let nextSent = $sentList[clickedResult.sent_id]["text"];
            $('#paper_modal').empty();
            $("#paper_modal").append('<textarea class="result_text_modal" name="text" readonly '+
                '                       id="text' + clickedResult.rel_id + '"'+ '>'+ nextSent +
                '                     </textarea>');
        });
    });
});



/*
SVG for the mini-graph
 */

var svg = d3.select("svg"),
    width = +svg.attr("width"),
    height = +svg.attr("height"),
    g = svg.append("g")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")")
        .attr("id", "minigraph");

var n = 2,
    r = 30;
var nodes = [{index: 0, x: 0, y: 0, vy: 0, vx: 0},
             {index: 1, x: 150, y: 0, vy: 0, vx: 0}];
//var links = d3.range(2).map(function(i) { return {source: i, target: (i + 3) % 2}; });
var links = [{
    source: {index: 0, x: 0, y: 0, vy: 0, vx: 0},
    target: {index: 1, x: 150, y: 0, vy: 0, vx: 0}
}];

var simulation = d3.forceSimulation(nodes)
    .force("charge", d3.forceManyBody().strength(-80))
    .force("link", d3.forceLink(links).distance(20).strength(1).iterations(10))
    .force("x", d3.forceX())
    .force("y", d3.forceY())
    .stop();

// arrow
g.append("marker")
    .attr("id", "triangle")
    .attr("refX", 6)
    .attr("refY", 6)
    .attr("markerWidth", 30)
    .attr("markerHeight", 30)
    .attr("markerUnits","userSpaceOnUse")
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M 0 0 12 6 0 12 3 6")
    .style("fill", "black");

// edge
g.append("g")
    .attr("stroke", "#000")
    .attr("stroke-width", 3)
    .selectAll("line")
    .data(links)
    .enter().append("line")
    //.attr("x1", function(d) { return d.source.x; })
    //.attr("y1", function(d) { return d.source.y; })
    .attr("x2", function(d) { return d.target.x - r - 6; }) // 6: dimension of the marker
    .attr("y2", function(d) { return d.target.y; })
    .attr("marker-end", "url(#triangle)");

// nodes
g.append("g")
    .attr("stroke", "#000")
    .attr("stroke-width", 2)
    .selectAll("circle")
    .data(nodes)
    .enter().append("circle")
    .attr("cx", function(d) { return d.x; })
    .attr("cy", function(d) { return d.y; })
    .attr("r", r)
    .style('fill', "red");


/*
$("#full_svg").append('<foreignobject class="node" x="0" y="110" width="100" height="100">\n' +
    '    <input id="prerequisite_node" type="text" name="prerequisite_node"/>\n' +
    '    </foreignobject>');
*/