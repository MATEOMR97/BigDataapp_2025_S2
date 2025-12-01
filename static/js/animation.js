function ejecutarAnimacion() {
  $('i').hide();

  // Pequeño delay para que se oculte visualmente antes de animar
  setTimeout(() => {
    $('i').show();

    var twitterPos = $('#twitter').position();
    var githubPos = $('#github').position();
    var stackPos = $('#stack').position();
    var linkedinPos = $('#linkedin').position();
    var codePos = $('#code').position();
    var plusPos = $('#plus').position();
    var mailPos = $('#mail').position();
    var imgPos = $('.me').position();

    $('i').css({
      position: 'absolute',
      zIndex: '1',
      top: imgPos.top + 100,
      left: '47%'
    });

    setTimeout(() => {
      $('#twitter').animate({
        top: twitterPos.top + 10,
        left: twitterPos.left - 10
      }, 500);
    }, 250);

    setTimeout(() => {
      $('#twitter').animate({ top: twitterPos.top, left: twitterPos.left }, 250);
      $('#github').animate({ top: githubPos.top + 10, left: githubPos.left - 6 }, 500);
    }, 500);

    setTimeout(() => {
      $('#github').animate({ top: githubPos.top, left: githubPos.left }, 250);
      $('#stack').animate({ top: stackPos.top + 10, left: stackPos.left - 3 }, 500);
    }, 750);

    setTimeout(() => {
      $('#stack').animate({ top: stackPos.top, left: stackPos.left }, 250);
      $('#linkedin').animate({ top: linkedinPos.top + 10, left: linkedinPos.left }, 500);
    }, 1000);

    setTimeout(() => {
      $('#linkedin').animate({ top: linkedinPos.top, left: linkedinPos.left }, 250);
      $('#code').animate({ top: codePos.top + 10, left: codePos.left + 3 }, 500);
    }, 1250);

    setTimeout(() => {
      $('#code').animate({ top: codePos.top, left: codePos.left }, 250);
      $('#plus').animate({ top: plusPos.top + 10, left: plusPos.left + 6 }, 500);
    }, 1500);

    setTimeout(() => {
      $('#plus').animate({ top: plusPos.top, left: plusPos.left }, 250);
      $('#mail').animate({ top: mailPos.top + 10, left: mailPos.left + 10 }, 500);
    }, 1750);

    setTimeout(() => {
      $('#mail').animate({ top: mailPos.top, left: mailPos.left }, 250);
    }, 2000);
  }, 50);
}

$(document).ready(function () {
  ejecutarAnimacion();
});
