// Modal Component

function createModal(title, content, footer = '') {
    const modalId = `modal-${Date.now()}`;
    
    const modalHTML = `
        <div class="modal-overlay" id="${modalId}">
            <div class="modal">
                <div class="modal-header">
                    <h3 class="modal-title">${escapeHtml(title)}</h3>
                    <button class="modal-close" onclick="closeModal('${modalId}')">×</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    const modal = document.getElementById(modalId);
    
    // Show modal
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
    
    // Close on overlay click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal(modalId);
        }
    });
    
    // Close on Escape key
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            closeModal(modalId);
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
    
    return modalId;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

// Make closeModal globally accessible
window.closeModal = closeModal;

function showConfirmModal(title, message, onConfirm, onCancel = null) {
    const modalId = `modal-${Date.now()}`;
    const content = `<p>${message}</p>`;
    const footer = `
        <button class="btn btn-secondary" id="cancelButton-${modalId}">Cancel</button>
        <button class="btn btn-danger" id="confirmButton-${modalId}">Confirm</button>
    `;
    
    const createdModalId = createModal(title, content, footer);
    const actualModalId = createdModalId || modalId;
    
    const confirmButton = document.getElementById(`confirmButton-${modalId}`);
    if (confirmButton) {
        confirmButton.addEventListener('click', () => {
            closeModal(actualModalId);
            if (onConfirm) onConfirm();
        });
    }
    
    if (onCancel) {
        const cancelButton = document.getElementById(`cancelButton-${modalId}`);
        if (cancelButton) {
            cancelButton.addEventListener('click', () => {
                closeModal(actualModalId);
                onCancel();
            });
        }
    }
}

