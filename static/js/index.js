function showExtension () {
  if (typeof chrome === 'undefined') {
    window.open('https://chrome.google.com/webstore/detail/mit-textbooks/ndgcomkciihbdocdhnhaekkkgblcgcml');
  } 
  else {
    chrome.webstore.install();
  }
}

$('.recents').easyTicker({
  direction: 'up',
  speed: 'slow',
  interval: 3000,
  height: 'auto',
  visible: 5,
  mousePause: 1
});