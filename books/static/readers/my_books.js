function onTabClick() {

  $(".tab-content").hide();
  $(".tab-btn").removeClass("active");
  $(this).addClass("active");

  var tabContentId = $(this).attr("data-tab-content-id");
  $(tabContentId).show();

  if ($(this).attr("id") == "tab-btn-my-readings") {
    loadAllReadings();
  }
}

function loadAllReadings() {
  $("#my-readings-list").empty();

  $.ajax({
    url: '/bookshelf/readings/',
    dataType: 'json',
    success: function(response) {
      $("#my-readings-list").empty();
      if (response.readings) {
        updateMyReadingsList(response.readings);
      }
    }
  });
}

function updateMyReadingsList(readings) {
  var statuses = {
    "R": "<span class='oi oi-pulse reading-progress-r'></span>",
    "F": "<span class='oi oi-check reading-progress-f'></span>",
    "A": "<span class='oi oi-x reading-progress-a'></span>"
  };

  for (var index in readings) {
    var reading = readings[index];
    var title = "<td class='my-readings-list-column'>" + reading.book_title + "</td>";
    var from = "<td class='my-readings-list-column align-middle my-readings-list-column-center'>" + reading.start_date + "</td>";
    var isEnded = reading.end_date != null;
    var to = "<td class='my-readings-list-column align-middle my-readings-list-column-center'>" + (isEnded ? reading.end_date : "") + "</td>";
    var progress = "<td class='my-readings-list-column align-middle my-readings-list-column-center'>" + statuses[reading.progress] + "</td>";
    $("#my-readings-list").append("<tr>" + title + from + to + progress + "</tr>");
  }
}

function updateMyBookRate(myBookRateTag, myBookRate) {
  myBookRateTag.attr("data-my-book-rate", myBookRate)

  for (i = 1; i <= 5; i++) {
    var star = myBookRateTag.children(".my-book-rate-star" + i)
    star.removeClass("active");
    star.text("star_border");
    if (i <= myBookRate) {
      $(star).addClass("active")
      star.text("star");
    }
  }
}

function onMyBookRateUnhover() {
  var myBookRateTag = $(this);
  var myBookRate = myBookRateTag.attr("data-my-book-rate");
  updateMyBookRate(myBookRateTag, myBookRate);
}

function onMyBookRateStarHover() {
  var myBookRateTag = $(this).parent(".my-book-rate");
  var index = parseInt($(this).attr("data-index"));

  for (i = 1; i <= 5; i++) {
    var star = myBookRateTag.children(".my-book-rate-star" + i);
    star.removeClass("active");
    star.text("star_border");
    if (i <= index) {
      $(star).addClass("active")
      star.text("star");
    }
  }
}

function onMyBookRateStarClick() {
  var myBookRateTag = $(this).parent(".my-book-rate");
  var isbn13 = myBookRateTag.attr("data-book-isbn");
  var myBookRate = parseInt($(this).attr("data-index"));
  updateMyBookRate(myBookRateTag, myBookRate);

  $.ajax({
    url: '/bookshelf/' + isbn13 + "/rate/",
    data: { "rate": myBookRate },
    dataType: 'json',
    type: 'POST',
    beforeSend: function(xhr, settings) {
      if (!this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", Cookies.get('csrftoken'));
      }
    },
    success: function(response) {
      console.log("r " + response);
      if (response.rate) {
        updateMyBookRate(myBookRateTag, response.rate);
      }
    }
  });
}

$(document).ready(function() {
  $(".tab-btn").click(onTabClick);
  $(".tab-btn-default").trigger("click");
  $(".my-book-rate").hover(function(){}, onMyBookRateUnhover);
  $(".my-book-rate-star").hover(onMyBookRateStarHover, function(){});
  $(".my-book-rate-star").click(onMyBookRateStarClick);
});