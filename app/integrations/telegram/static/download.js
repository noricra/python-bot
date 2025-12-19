// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Get parameters from URL
const urlParams = new URLSearchParams(window.location.search);
const productId = urlParams.get('product_id');
const userLang = urlParams.get('lang') || 'fr';

// Translations
const translations = {
    fr: {
        notInTelegram: 'Cette application doit être ouverte depuis Telegram.',
        useButton: 'Utilisez le bouton "📥 Télécharger" dans le bot.',
        error: 'Erreur',
        verifying: 'Vérification de votre achat...',
        notPurchased: 'Vous n\'avez pas acheté ce produit.',
        fileNotAvailable: 'Fichier non disponible.',
        downloadError: 'Erreur lors du téléchargement',
        networkError: 'Erreur réseau. Vérifiez votre connexion.',
        unknownError: 'Une erreur inconnue est survenue.'
    },
    en: {
        notInTelegram: 'This application must be opened from Telegram.',
        useButton: 'Use the "📥 Download" button in the bot.',
        error: 'Error',
        verifying: 'Verifying your purchase...',
        notPurchased: 'You have not purchased this product.',
        fileNotAvailable: 'File not available.',
        downloadError: 'Download error',
        networkError: 'Network error. Check your connection.',
        unknownError: 'An unknown error occurred.'
    }
};

// Translation helper
const t = (key) => translations[userLang][key] || translations['fr'][key];

// Vérifier que l'app est bien dans Telegram
if (!tg.initData || tg.initData.length === 0) {
    console.error('❌ Not running in Telegram WebApp or initData is empty');
    document.body.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <h2>⚠️ ${t('error')}</h2>
            <p>${t('notInTelegram')}</p>
            <p>${t('useButton')}</p>
        </div>
    `;
    throw new Error('Not in Telegram WebApp');
}

// Get user data from Telegram
const userId = tg.initDataUnsafe?.user?.id;
const username = tg.initDataUnsafe?.user?.username;

// Log for debugging
console.log('✅ Telegram WebApp initialized');
console.log('User ID:', userId);
console.log('Product ID:', productId);

// DOM Elements
const loadingSection = document.getElementById('loadingSection');
const productSection = document.getElementById('productSection');
const progressSection = document.getElementById('progressSection');
const successSection = document.getElementById('successSection');
const errorSection = document.getElementById('errorSection');

const productTitle = document.getElementById('productTitle');
const productSize = document.getElementById('productSize');
const downloadCount = document.getElementById('downloadCount');
const downloadBtn = document.getElementById('downloadBtn');

const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const downloadSpeed = document.getElementById('downloadSpeed');
const fileName = document.getElementById('fileName');
const downloadedSize = document.getElementById('downloadedSize');
const totalSize = document.getElementById('totalSize');

const successFileName = document.getElementById('successFileName');
const errorMessage = document.getElementById('errorMessage');

// Global variables
let purchaseData = null;

// Show/hide sections helper
function showSection(sectionId) {
    const sections = ['loadingSection', 'productSection', 'progressSection', 'successSection', 'errorSection'];
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            if (id === sectionId) {
                element.classList.remove('hidden');
            } else {
                element.classList.add('hidden');
            }
        }
    });
}

// Show error
function showError(message) {
    errorMessage.textContent = message;
    showSection('errorSection');
}

// Format file size
function formatFileSize(mb) {
    if (mb < 1) {
        return `${(mb * 1024).toFixed(2)} KB`;
    } else if (mb < 1024) {
        return `${mb.toFixed(2)} MB`;
    } else {
        return `${(mb / 1024).toFixed(2)} GB`;
    }
}

// Verify purchase on page load
async function verifyPurchase() {
    if (!productId) {
        showError('Product ID manquant dans l\'URL');
        return;
    }

    try {
        console.log('🔍 Verifying purchase...');
        const response = await fetch('/api/verify-purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_id: productId,
                user_id: userId,
                telegram_init_data: tg.initData
            })
        });

        if (!response.ok) {
            if (response.status === 404) {
                showError(t('notPurchased'));
                return;
            } else if (response.status === 401) {
                showError('Authentification échouée');
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ Purchase verified:', data);
        purchaseData = data;

        // Display product info
        productTitle.textContent = data.product_title;
        productSize.textContent = `📦 Taille: ${formatFileSize(data.file_size_mb)}`;

        const downloadCountText = userLang === 'fr'
            ? `Téléchargé ${data.download_count} fois`
            : `Downloaded ${data.download_count} times`;
        downloadCount.textContent = `📊 ${downloadCountText}`;

        // Check if file is available
        if (!data.has_file) {
            showError(t('fileNotAvailable'));
            return;
        }

        // Show product section
        showSection('productSection');

    } catch (error) {
        console.error('❌ Error verifying purchase:', error);
        showError(t('networkError'));
    }
}

// Handle download button click
downloadBtn.addEventListener('click', async () => {
    if (!purchaseData) {
        showError('Purchase data not available');
        return;
    }

    try {
        console.log('📥 Requesting download URL...');
        showSection('progressSection');

        // Request presigned download URL
        const response = await fetch('/api/generate-download-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_id: purchaseData.product_id,
                order_id: purchaseData.order_id,
                user_id: userId,
                telegram_init_data: tg.initData
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ Download URL received');

        fileName.textContent = data.file_name;
        totalSize.textContent = formatFileSize(data.file_size_mb);

        // Start download with progress tracking
        await downloadFile(data.download_url, data.file_name, data.file_size_mb);

    } catch (error) {
        console.error('❌ Error downloading:', error);
        showError(t('downloadError'));
    }
});

// Download file with progress tracking
async function downloadFile(url, filename, fileSizeMb) {
    try {
        console.log('⬇️ Downloading file...');

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const contentLength = response.headers.get('Content-Length');
        const total = parseInt(contentLength, 10);

        if (!total || isNaN(total)) {
            // Fallback: no progress tracking
            console.warn('⚠️ Content-Length not available, downloading without progress');
            const blob = await response.blob();
            triggerDownload(blob, filename);
            return;
        }

        // Download with progress tracking
        const reader = response.body.getReader();
        const chunks = [];
        let receivedLength = 0;
        const startTime = Date.now();

        while(true) {
            const {done, value} = await reader.read();

            if (done) {
                break;
            }

            chunks.push(value);
            receivedLength += value.length;

            // Update progress
            const percent = Math.round((receivedLength / total) * 100);
            const elapsedSeconds = (Date.now() - startTime) / 1000;
            const speed = (receivedLength / 1024 / 1024) / elapsedSeconds;

            progressBar.style.width = `${percent}%`;
            progressPercent.textContent = `${percent}%`;
            downloadSpeed.textContent = `${speed.toFixed(2)} MB/s`;
            downloadedSize.textContent = formatFileSize(receivedLength / 1024 / 1024);
        }

        // Combine chunks into blob
        const blob = new Blob(chunks);
        console.log('✅ Download complete');

        // Trigger browser download
        triggerDownload(blob, filename);

        // Show success
        successFileName.textContent = filename;
        showSection('successSection');

    } catch (error) {
        console.error('❌ Download error:', error);
        showError(t('downloadError'));
    }
}

// Trigger browser download
function triggerDownload(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    console.log('✅ File download triggered');
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    verifyPurchase();
});

// Handle errors globally
window.addEventListener('error', (event) => {
    console.error('💥 Global error:', event.error);
    // Send error to backend for logging
    fetch('/api/log-client-error', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            error_type: 'download_error',
            details: {
                message: event.error?.message || 'Unknown error',
                stack: event.error?.stack,
                product_id: productId,
                user_id: userId
            },
            user_id: userId
        })
    }).catch(err => console.error('Failed to log error:', err));
});
