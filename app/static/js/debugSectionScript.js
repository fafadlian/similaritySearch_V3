document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.nav-link-container .nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault(); // Stop the default anchor action
            const sections = document.querySelectorAll('main > section');
            // Hide all sections
            sections.forEach(section => {
                section.style.display = 'none';
            });

            // Show the targeted section
            const targetSectionId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetSectionId);
            if (targetSection) {
                targetSection.style.display = 'block';
            }
        });
    });
});

link.addEventListener('click', function(e) {
    console.log("Link clicked:", this.getAttribute('href')); // Or use alert for more obvious feedback
    // Rest of the code...
});
