// Thai House Coin Exchange - minimal JS
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    document.querySelectorAll('.flash').forEach(function(el) {
        setTimeout(function() {
            el.style.transition = 'opacity 0.5s';
            el.style.opacity = '0';
            setTimeout(function() { el.remove(); }, 500);
        }, 5000);
    });
});
