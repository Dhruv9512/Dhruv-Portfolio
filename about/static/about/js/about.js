const navLinks = document.querySelectorAll('#section-nav a');

navLinks.forEach(link => {
  link.addEventListener('click', function() {
    navLinks.forEach(l => l.classList.remove('active')); 
    this.classList.add('active'); 
  });
});

// Add 'active' class to the first link when the page loads
document.addEventListener('DOMContentLoaded', function() {
    navLinks[0].classList.add('active');
});