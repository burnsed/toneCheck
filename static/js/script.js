function show_error_message(error_message){
    var error_box = $("#error-modal");
    var error_txt = $('#error-modal p');
    error_txt.text(error_message);
    $('#error-modal').modal('show');
}

var uploadSetup = function() {
    $("#upload-file-input").change(function(event) {
        event.preventDefault();

        var files = event.target.files;
        var data = new FormData();
        $.each(files, function(k,v) {
            data.append(k,v);
        });

        // Upload the file
        fetch("/parse-file", {
            method: 'POST',
            body: data,
        }).then(response => response.json()).then(data => {
            if (data["success"]) {
                // Success
                $('#success-modal').modal('show');

                // reload page
                setTimeout(function() {
                    location.reload();
                }, 1500);
            } else {
                console.log(data["error_message"]);
                show_error_message(data["error_message"]);
            }
        }).catch(error => {
            console.log(error);
            show_error_message(error);
        });
    });
};


$(document).ready(function(){
    uploadSetup();
})
