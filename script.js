// JavaScript for EduPay - Secure Implementation
document.addEventListener('DOMContentLoaded', function() {
    'use strict'; // Enable strict mode for better security
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
    
    // Form validation for payment amount
    const paymentForms = document.querySelectorAll('form')
    paymentForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const amountInput = form.querySelector('#amount')
            if (amountInput) {
                const amount = parseFloat(amountInput.value)
                if (amount <= 0 || isNaN(amount) || !isFinite(amount)) {
                    e.preventDefault()
                    // Use proper error display instead of alert
                    const errorDiv = document.createElement('div')
                    errorDiv.className = 'alert alert-danger mt-2'
                    errorDiv.textContent = 'Please enter a valid amount greater than zero'
                    
                    // Remove existing error messages
                    const existingError = form.querySelector('.alert-danger')
                    if (existingError) existingError.remove()
                    
                    amountInput.parentNode.appendChild(errorDiv)
                    amountInput.focus()
                }
            }
        })
    })
    
    // Auto-focus username field on login page with null check
    if (window.location.pathname === '/login') {
        const usernameField = document.getElementById('username')
        if (usernameField) {
            usernameField.focus()
        }
    }
    
    // Show loading state on form submissions (reuse forms variable)
    paymentForms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitButton = form.querySelector('button[type="submit"]')
            if (submitButton) {
                // Use textContent to prevent XSS
                submitButton.innerHTML = ''
                const spinner = document.createElement('span')
                spinner.className = 'spinner-border spinner-border-sm'
                spinner.setAttribute('role', 'status')
                spinner.setAttribute('aria-hidden', 'true')
                submitButton.appendChild(spinner)
                submitButton.appendChild(document.createTextNode(' Processing...'))
                submitButton.disabled = true
            }
        })
    })
})