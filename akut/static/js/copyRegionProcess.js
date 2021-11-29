$(document).ready(function() {

	$('.formSave').on('submit', function(event) {

		$.ajax({
			data : {
				dataset: JSON.stringify({
					from: document.getElementById("inputFrom").value,
					to: document.getElementById("inputTo").value
				})
			},
			type : 'POST',
			url : '/copyRegion_process'
		})
		.done(function(data) {

            if (data.error) {
				$('#errorAlert').text(data.error).show();
				$('#successAlert').hide();
			}
			else {
				$('#successAlert').text(data.success).show();
				$('#errorAlert').hide();
			}

		});

		event.preventDefault();

	});

});