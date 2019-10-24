$('body').mouseup(function(){
   var span = document.createElement("span");
    if (window.getSelection().toString()) {
        var sel = window.getSelection();
        
        if (sel.rangeCount) {
          var range = sel.getRangeAt(0).cloneRange();
          var node = $(range.commonAncestorContainer)
          if(node.parent().is("span")) {
            node.unwrap();
          }
          else if (hasNumber(sel.toString())) {
             var range = sel.getRangeAt(0).cloneRange();
             range.surroundContents(span);
             sel.removeAllRanges();
             sel.addRange(range);
             console.log(sel.toString())
            }
        }
  }
});

function hasNumber(myString) {
  return /\d/.test(myString);
}

window.onload = function() {
    var fileInput = document.getElementById('customFile');
    var fileDisplayArea = document.getElementById('content-target');

    fileInput.addEventListener('change', function(e) {
    var file = fileInput.files[0];
    var textType = /text.*/;

    if (file.type.match(textType)) {
        var reader = new FileReader();

        reader.onload = function(e) {
        fileDisplayArea.innerText = reader.result;
        }

        reader.readAsText(file);    
    } else {
        fileDisplayArea.innerText = "File not supported!"
      }
    });
}


//code to make the name of the file appear on select
$(".custom-file-input").on("change", function() {
    var fileName = $(this).val().split("\\").pop();
    $(this).siblings(".custom-file-label").addClass("selected").html(fileName);
});



function getValue() {
$(function() {
    result = Array.prototype.filter.call(document.getElementsByTagName("span"),
                 function (elm) { return /\d/.test(elm.innerHTML) }
             ); 
    return result;
});
}


function submit_entry() {
    
    var book = document.getElementById("book")
    var author = document.getElementById("author")
    var year = document.getElementById("year")
    var cap = document.getElementById("cap")
    var category = document.getElementById("category")
    var text = document.getElementById("content-target")
    var result = Array.prototype.filter.call(
             $("span"),
                 function (elm) { return /\d/.test(elm.innerHTML) }
             );

    result.forEach(function(part, index) {
      this[index] = this[index].innerHTML;
    }, result)

    var entry = {
        book: book.value,
        author: author.value,
        year: year.value,
        cap: cap.value,
        category: category.value,
        text: text.outerText,
        result: result
    };
    document.body.classList.add("loading");
    
    fetch('/text_upload', {
        method: "POST",
        credentials: "include",
        body: JSON.stringify(entry),
        cache: "no-cache",
        headers: new Headers({
            "content-type": "application/json"
        })
    
    })
    .then(function (response) {
    
        document.body.classList.remove("loading");
        if (response.status !== 200) {
        
            document.getElementById('bootstrap-alert').style.display = 'block';
            setTimeout(function(){document.getElementById('bootstrap-alert').style.display = 'none'}, 1700);
  
            //THIS IS JS ALERT
            alert(data);
                   
          }
        
        response.json().then(function(data) {
        
            document.getElementById('bootstrap-alert').style.display = 'block';
            setTimeout(function(){document.getElementById('bootstrap-alert').style.display = 'none'}, 1700);
  
            //THIS IS JS ALERT
            alert(data);
            
        })
    })

}


 



