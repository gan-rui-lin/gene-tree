/* ===== Toast Notifications ===== */
function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    if (!container) return;

    var colorMap = {
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning text-dark',
        info: 'bg-primary'
    };
    var iconMap = {
        success: '✔',
        error: '✘',
        warning: '⚠',
        info: 'ℹ'
    };

    var toast = document.createElement('div');
    toast.className = 'toast align-items-center border-0 show';
    toast.setAttribute('role', 'alert');
    toast.style.minWidth = '280px';
    toast.innerHTML =
        '<div class="d-flex">' +
            '<div class="toast-body d-flex align-items-center gap-2">' +
                '<span class="rounded-circle d-inline-flex align-items-center justify-content-center ' + colorMap[type] + '" style="width:24px;height:24px;color:#fff;font-size:13px;">' + iconMap[type] + '</span>' +
                '<span>' + message + '</span>' +
            '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest(\'.toast\').remove()"></button>' +
        '</div>';

    container.appendChild(toast);
    setTimeout(function() {
        toast.classList.remove('show');
        toast.classList.add('hide');
        setTimeout(function() { toast.remove(); }, 300);
    }, 3500);
}

/* ===== Form Submit Loading ===== */
function initFormLoading() {
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            var btn = form.querySelector('button[type="submit"], button:not([type])');
            if (btn && !btn.dataset.noLoading) {
                btn.disabled = true;
                btn.dataset.originalText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>' + btn.textContent.trim();
            }
        });
    });
}

/* ===== Input Validation Feedback ===== */
function initValidation() {
    document.querySelectorAll('.form-control[required], .form-select[required]').forEach(function(input) {
        input.addEventListener('invalid', function(e) {
            e.preventDefault();
            input.classList.add('is-invalid');
        });
        input.addEventListener('input', function() {
            input.classList.remove('is-invalid');
            if (input.value.trim()) {
                input.classList.add('is-valid');
            } else {
                input.classList.remove('is-valid');
            }
        });
    });
}

/* ===== Show Server Messages as Toast ===== */
function showServerMessages() {
    var params = new URLSearchParams(window.location.search);
    var status = params.get('status');
    var error = params.get('error');
    if (status) showToast(decodeURIComponent(status), 'success');
    if (error) showToast(decodeURIComponent(error), 'error');

    if (status || error) {
        var url = new URL(window.location);
        url.searchParams.delete('status');
        url.searchParams.delete('error');
        window.history.replaceState({}, '', url);
    }
}

/* ===== Init ===== */
document.addEventListener('DOMContentLoaded', function() {
    initFormLoading();
    initValidation();
    showServerMessages();
    initTheme();
});

/* ===== Theme Toggle ===== */
function initTheme() {
    var saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

function toggleTheme() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    }
}
