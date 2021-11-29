$(document).ready(function() {

	$('form').on('submit', function(event) {

		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/computeMassnahmenKataster_process'
		})
		.done(function(data) {

			if (data.error) {
				$('#errorAlert').text(data.error).show();
				$('#successAlert').hide();
			}
			else {
				$('#successAlert').text(data.dataset).show();
				$('#errorAlert').hide();
			}

		});

		event.preventDefault();

	});

});