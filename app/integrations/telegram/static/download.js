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
    console.error('Not running in Telegram WebApp or initData is empty');
    document.body.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <h2>${t('error')}</h2>
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
console.log('Telegram WebApp initialized');
console.log('User ID:', userId);
console.log('Product ID:', productId);

// Global variables
let purchaseData = null;

// DOM Elements (will be set after DOM loads)
let loadingSection, productSection, progressSection, successSection, errorSection;
let productTitle, productSize, downloadCount, downloadBtn;
let progressBar, progressPercent, downloadSpeed, fileName, downloadedSize, totalSize;
let successFileName, errorMessage;

// Initialize DOM elements
function initDOMElements() {
    loadingSection = document.getElementById('loadingSection');
    productSection = document.getElementById('productSection');
    progressSection = document.getElementById('progressSection');
    successSection = document.getElementById('successSection');
    errorSection = document.getElementById('errorSection');

    productTitle = document.getElementById('productTitle');
    productSize = document.getElementById('productSize');
    downloadCount = document.getElementById('downloadCount');
    downloadBtn = document.getElementById('downloadBtn');

    progressBar = document.getElementById('progressBar');
    progressPercent = document.getElementById('progressPercent');
    downloadSpeed = document.getElementById('downloadSpeed');
    fileName = document.getElementById('fileName');
    downloadedSize = document.getElementById('downloadedSize');
    totalSize = document.getElementById('totalSize');

    successFileName = document.getElementById('successFileName');
    errorMessage = document.getElementById('errorMessage');
}

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
        console.error('❌ [VERIFY] Product ID manquant dans l\'URL');
        showError('Product ID manquant dans l\'URL');
        return;
    }

    try {
        const requestBody = {
            product_id: productId,
            user_id: userId,
            telegram_init_data: tg.initData
        };
        console.log('🔍 [VERIFY] Starting verification with params:', {
            product_id: productId,
            user_id: userId,
            initData_length: tg.initData?.length || 0
        });

        const response = await fetch('/api/verify-purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        console.log(`📡 [VERIFY] Response status: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorDetail = errorData.detail || `HTTP ${response.status}`;
            console.error('❌ [VERIFY] API Error:', {
                status: response.status,
                statusText: response.statusText,
                detail: errorDetail,
                fullError: errorData
            });

            if (response.status === 404) {
                showError(t('notPurchased'));
                return;
            } else if (response.status === 401) {
                showError('Authentification échouée: ' + errorDetail);
                return;
            }
            showError(`Erreur ${response.status}: ${errorDetail}`);
            return;
        }

        const data = await response.json();
        console.log('✅ [VERIFY] Purchase verified successfully:', data);
        purchaseData = data;

        // Display product info
        productTitle.textContent = data.product_title;
        productSize.textContent = `Taille: ${formatFileSize(data.file_size_mb)}`;

        const downloadCountText = userLang === 'fr'
            ? `Téléchargé ${data.download_count} fois`
            : `Downloaded ${data.download_count} times`;
        downloadCount.textContent = downloadCountText;

        // Check if file is available
        if (!data.has_file) {
            showError(t('fileNotAvailable'));
            return;
        }

        // Show product section
        showSection('productSection');

    } catch (error) {
        console.error('Error verifying purchase:', error);
        showError(t('networkError'));
    }
}

// Handle download button click
function setupDownloadButton() {
    downloadBtn.addEventListener('click', async () => {
        if (!purchaseData) {
            console.error('[DOWNLOAD] Purchase data not available');
            showError('Purchase data not available');
            return;
        }

        try {
            const requestBody = {
                product_id: purchaseData.product_id,
                order_id: purchaseData.order_id,
                user_id: userId,
                telegram_init_data: tg.initData
            };
            console.error('========== USING NEW PROXY ENDPOINT ==========');
            console.error('[DOWNLOAD] Calling /api/stream-download (NEW PROXY)');
            console.log('[DOWNLOAD] Starting stream download with params:', {
                product_id: purchaseData.product_id,
                order_id: purchaseData.order_id,
                user_id: userId,
                initData_length: tg.initData?.length || 0
            });

            showSection('progressSection');
            fileName.textContent = purchaseData.product_title || 'file';
            totalSize.textContent = formatFileSize(purchaseData.file_size_mb);

            // Appel proxy backend
            console.error('[DOWNLOAD] Fetching /api/stream-download...');
            const response = await fetch('/api/stream-download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            console.error(`[DOWNLOAD] Stream response: ${response.status} ${response.statusText}`);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorDetail = errorData.detail || `HTTP ${response.status}`;
                console.error('========== STREAM-DOWNLOAD ERROR ==========');
                console.error('[DOWNLOAD] Stream error:', {
                    status: response.status,
                    statusText: response.statusText,
                    detail: errorDetail,
                    fullResponse: errorData
                });
                showError(`Erreur telechargement: ${errorDetail}`);
                return;
            }

            console.error('[DOWNLOAD] Response OK, starting stream read...');

            // Stream avec progress tracking
            const contentLength = response.headers.get('Content-Length');
            const total = parseInt(contentLength, 10);
            const reader = response.body.getReader();
            const chunks = [];
            let receivedLength = 0;
            const startTime = Date.now();

            console.log('[DOWNLOAD] Starting stream read, content-length:', contentLength);

            while(true) {
                const {done, value} = await reader.read();
                if (done) {
                    console.log('[DOWNLOAD] Stream read completed');
                    break;
                }

                chunks.push(value);
                receivedLength += value.length;

                // Update progress UI
                const percent = Math.round((receivedLength / total) * 100);
                const elapsedSeconds = (Date.now() - startTime) / 1000;
                const speed = (receivedLength / 1024 / 1024) / elapsedSeconds;

                progressBar.style.width = `${percent}%`;
                progressPercent.textContent = `${percent}%`;
                downloadSpeed.textContent = `${speed.toFixed(2)} MB/s`;
                downloadedSize.textContent = formatFileSize(receivedLength / 1024 / 1024);

                // Log progress every 25%
                if (percent % 25 === 0 && percent > 0) {
                    console.log(`[DOWNLOAD] Progress: ${percent}% (${receivedLength}/${total} bytes)`);
                }
            }

            // Trigger download
            const blob = new Blob(chunks);
            const filename = purchaseData.product_title || 'download';
            console.error('[DOWNLOAD] Creating blob:', {
                size: blob.size,
                expected: total,
                match: blob.size === total
            });

            triggerDownload(blob, filename);

            // Show success
            successFileName.textContent = filename;
            showSection('successSection');
            console.error('========== DOWNLOAD SUCCESS ==========');
            console.error('[DOWNLOAD] Download completed successfully');

        } catch (error) {
            console.error('[DOWNLOAD] Exception:', {
                message: error.message,
                stack: error.stack
            });
            showError(t('downloadError'));
        }
    });
}

// Download file with progress tracking
async function downloadFile(url, filename, fileSizeMb) {
    try {
        console.log('📦 [FILE] Starting file download:', {
            filename: filename,
            expected_size_mb: fileSizeMb,
            url_length: url?.length || 0,
            url_preview: url?.substring(0, 100) + '...'
        });

        const response = await fetch(url);

        console.log(`📡 [FILE] B2 Response:`, {
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries([...response.headers.entries()]),
            ok: response.ok
        });

        if (!response.ok) {
            console.error('❌ [FILE] Download failed:', {
                status: response.status,
                statusText: response.statusText
            });
            throw new Error(`Téléchargement échoué: ${response.status} ${response.statusText}`);
        }

        const contentLength = response.headers.get('Content-Length');
        const total = parseInt(contentLength, 10);

        console.log(`📊 [FILE] Content-Length: ${contentLength} (${total} bytes)`);

        if (!total || isNaN(total)) {
            // Fallback: no progress tracking
            console.warn('⚠️ [FILE] Content-Length not available, downloading without progress');
            const blob = await response.blob();
            console.log(`✅ [FILE] Blob created: ${blob.size} bytes, type: ${blob.type}`);
            triggerDownload(blob, filename);
            return;
        }

        // Download with progress tracking
        console.log('📥 [FILE] Starting streaming download with progress tracking');
        const reader = response.body.getReader();
        const chunks = [];
        let receivedLength = 0;
        const startTime = Date.now();

        while(true) {
            const {done, value} = await reader.read();

            if (done) {
                console.log('✅ [FILE] Stream complete');
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

            // Log progress every 25%
            if (percent % 25 === 0 && percent > 0) {
                console.log(`📊 [FILE] Progress: ${percent}% (${receivedLength}/${total} bytes, ${speed.toFixed(2)} MB/s)`);
            }
        }

        // Combine chunks into blob
        const blob = new Blob(chunks);
        console.log('✅ [FILE] Download complete:', {
            total_chunks: chunks.length,
            blob_size: blob.size,
            blob_type: blob.type,
            expected_size: total,
            match: blob.size === total
        });

        // Trigger browser download
        triggerDownload(blob, filename);

        // Show success
        successFileName.textContent = filename;
        showSection('successSection');

    } catch (error) {
        console.error('❌ [FILE] Download error:', {
            message: error.message,
            stack: error.stack,
            error: error
        });
        showError(t('downloadError'));
    }
}

// Trigger browser download
function triggerDownload(blob, filename) {
    console.log('💾 [TRIGGER] Creating download trigger:', {
        blob_size: blob.size,
        blob_type: blob.type,
        filename: filename
    });

    const url = window.URL.createObjectURL(blob);
    console.log('🔗 [TRIGGER] Object URL created:', url.substring(0, 50) + '...');

    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);

    console.log('🖱️ [TRIGGER] Clicking download link...');
    a.click();

    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    console.log('✅ [TRIGGER] File download triggered successfully');
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    initDOMElements();
    setupDownloadButton();
    verifyPurchase();
});

// Handle errors globally
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
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
