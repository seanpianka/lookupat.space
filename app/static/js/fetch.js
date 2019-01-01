$(document).ready(function() {
  var win = $(window);
  var url = '/fetch/5b242458c632ddb37d2e00b2f30dca144b8de39d08d3b20fdadbfcff0fc8a25f';
  var ready = true;
  let LOADING_BAR = $('#loading');
  let CONTENT_AREA =$('#content');

  $.ajax({
    url: url,
    dataType: 'html',
    success: function(html)
    {
      CONTENT_AREA.append(html);
      LOADING_BAR.hide();
    }
  });

  // Each time the user scrolls
  $(window).bind('scroll', function()
  {
    // End of the document reached?
    if (ready && $(document).height() - $(window).scrollTop() <= 3000)
    {
      $('#loading').show();
      $.ajax({
        url: url,
        dataType: 'html',
        success: function(html)
        {
          CONTENT_AREA.append(html);
          LOADING_BAR.hide();
        }
      });
      ready = false;
      setTimeout(function(){ ready = true; }, 500)
    }
  });
});
