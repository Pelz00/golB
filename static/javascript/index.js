document.addEventListener('DOMContentLoaded', function () {
    const flashes = document.querySelectorAll('.flash-msg');
    flashes.forEach(function (flash) {
        setTimeout(() => {
           flash.computedStyleMap.transition = 'opacity 0.5s';
           flash.computedStyleMap.opacity = '0'; 
           setTimeout(() => flash.remove(), 500)
        }, 4000);
    })
})

document.addEventListener('DOMContentLoaded', function () {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(function (flash) {
        setTimeout(() => {
           flash.computedStyleMap.transition = 'opacity 0.5s';
           flash.computedStyleMap.opacity = '0'; 
           setTimeout(() => flash.remove(), 500)
        }, 4000);
    })
})