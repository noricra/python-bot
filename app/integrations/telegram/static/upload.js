// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Configure PDF.js worker
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

// Get language from URL parameter
const urlParams = new URLSearchParams(window.location.search);
const userLang = urlParams.get('lang') || 'fr';

// Translations
const translations = {
    fr: {
        notInTelegram: 'Cette application doit être ouverte depuis Telegram.',
        useButton: 'Utilisez le bouton "📤 Upload via Mini App" dans le bot.',
        error: 'Erreur',
        fileTooLarge: 'Fichier trop volumineux (max 10 GB)',
        preparing: 'Préparation...',
        generatingPreview: 'Génération aperçu...',
        uploadingPreview: 'Upload aperçu...',
        uploadError: "Erreur lors de l'upload"
    },
    en: {
        notInTelegram: 'This application must be opened from Telegram.',
        useButton: 'Use the "📤 Upload via Mini App" button in the bot.',
        error: 'Error',
        fileTooLarge: 'File too large (max 10 GB)',
        preparing: 'Preparing...',
        generatingPreview: 'Generating preview...',
        uploadingPreview: 'Uploading preview...',
        uploadError: 'Upload error'
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
console.log('Init data length:', tg.initData.length);

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const progressSection = document.getElementById('progressSection');
const successSection = document.getElementById('successSection');
const errorSection = document.getElementById('errorSection');
const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const uploadSpeed = document.getElementById('uploadSpeed');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const errorMessage = document.getElementById('errorMessage');

// Drag & Drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelection(files[0]);
    }
});

// File Input
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
    }
});

// Generate PDF Preview (first page as PNG)
async function generatePDFPreview(file) {
    try {
        console.log('📄 Generating PDF preview...');

        // Read file as ArrayBuffer
        const arrayBuffer = await file.arrayBuffer();

        // Load PDF document
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        console.log(`📄 PDF loaded: ${pdf.numPages} pages`);

        // Render first page
        const page = await pdf.getPage(1);
        const viewport = page.getViewport({ scale: 2.0 });

        // Create canvas
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = viewport.width;
        canvas.height = viewport.height;

        // Render PDF page to canvas
        await page.render({
            canvasContext: context,
            viewport: viewport
        }).promise;

        console.log('✅ PDF preview rendered to canvas');

        // Convert canvas to PNG blob
        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                console.log(`✅ Preview PNG generated: ${formatBytes(blob.size)}`);
                resolve(blob);
            }, 'image/png', 0.9);
        });
    } catch (error) {
        console.error('❌ PDF preview generation failed:', error);
        return null;
    }
}

// Handle File Selection
async function handleFileSelection(file) {
    console.log('File selected:', file.name, formatBytes(file.size));

    // Validation
    const maxSize = 10 * 1024 * 1024 * 1024; // 10 GB
    if (file.size > maxSize) {
        showError(t('fileTooLarge'));
        return;
    }

    // Update UI
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);

    uploadArea.classList.add('hidden');
    progressSection.classList.remove('hidden');

    // ✅ NOUVEAU FLUX: Générer product_id AVANT tout upload
    try {
        // 1️⃣ Request main file upload URL (génère product_id)
        progressPercent.textContent = t('preparing');
        const uploadData = await requestPresignedUploadURL(file.name, file.type, userId);

        if (!uploadData || !uploadData.upload_url || !uploadData.product_id) {
            throw new Error('Failed to get upload URL or product_id');
        }

        const productId = uploadData.product_id;
        console.log('🆔 Product ID received:', productId);

        // 2️⃣ Si PDF, générer et uploader preview (utilise product_id)
        let previewUrl = null;
        const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

        if (isPDF) {
            try {
                console.log('📄 PDF detected, generating preview...');
                progressPercent.textContent = t('generatingPreview');

                const previewBlob = await generatePDFPreview(file);

                if (previewBlob) {
                    console.log('📤 Uploading preview to B2...');
                    progressPercent.textContent = t('uploadingPreview');

                    // ✅ Construire URL preview avec MÊME product_id
                    const previewObjectKey = `products/${userId}/${productId}/preview.png`;
                    console.log('📸 Preview path:', previewObjectKey);

                    // Get upload URL for preview (sans générer nouveau product_id)
                    const b2 = await getB2UploadUrlForPath(previewObjectKey, 'image/png');

                    if (b2) {
                        await uploadFileToB2(previewBlob, b2);
                        previewUrl = `https://s3.us-west-004.backblazeb2.com/${previewObjectKey}`;
                        console.log('✅ Preview uploaded:', previewUrl);
                    }
                }
            } catch (error) {
                console.warn('⚠️ Preview generation failed, continuing without preview:', error);
            }
        }

        // 3️⃣ Upload main file
        progressPercent.textContent = '0%';
        console.log('📤 Uploading main file to:', uploadData.object_key);
        await uploadFileToB2(file, uploadData);

        // 4️⃣ Notify backend
        await notifyUploadComplete(uploadData.object_key, file.name, file.size, previewUrl);

        // 5️⃣ Success
        showSuccess();

    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message || t('uploadError'));
    }
}

// Request Presigned Upload URL from Backend
async function requestPresignedUploadURL(fileName, fileType, userId) {
    console.log('📤 Requesting presigned URL...');

    const response = await fetch('/api/generate-upload-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            file_name: fileName,
            file_type: fileType,
            user_id: userId,
            telegram_init_data: tg.initData  // For auth verification
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.detail || `HTTP ${response.status}`;
        console.error('❌ Failed to get upload URL:', errorMsg);
        throw new Error(`Erreur serveur: ${errorMsg}`);
    }

    const data = await response.json();
    console.log('✅ Presigned URL received');
    return data;
}

// Get B2 upload URL for a specific path (for preview)
async function getB2UploadUrlForPath(objectKey, contentType) {
    console.log('📤 Requesting B2 URL for path:', objectKey);

    const response = await fetch('/api/get-b2-upload-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            object_key: objectKey,
            content_type: contentType,
            user_id: userId,
            telegram_init_data: tg.initData
        })
    });

    if (!response.ok) {
        console.error('❌ Failed to get B2 upload URL for path');
        return null;
    }

    const data = await response.json();
    console.log('✅ B2 upload URL received for path');
    return data;
}

// Upload File to B2 via Native API (CORS-compatible)
async function uploadFileToB2(file, uploadData) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        // Track upload progress
        let startTime = Date.now();
        let lastLoaded = 0;

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                progressBar.style.width = percent + '%';
                progressPercent.textContent = Math.round(percent) + '%';

                // Calculate upload speed
                const elapsed = (Date.now() - startTime) / 1000; // seconds
                const speed = (e.loaded - lastLoaded) / elapsed / (1024 * 1024); // MB/s
                uploadSpeed.textContent = speed.toFixed(2) + ' MB/s';

                lastLoaded = e.loaded;
                startTime = Date.now();
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                console.log('✅ Upload successful:', xhr.responseText);
                resolve();
            } else {
                // Log HTTP error details
                const errorDetails = {
                    status: xhr.status,
                    statusText: xhr.statusText,
                    responseText: xhr.responseText || 'No response'
                };
                console.error('❌ Upload HTTP Error:', errorDetails);

                // Send to backend for logging
                fetch('/api/log-client-error', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        error_type: 'xhr_http_error',
                        details: errorDetails,
                        user_id: userId
                    })
                }).catch(() => {});

                reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
            }
        });

        xhr.addEventListener('error', () => {
            // Capture detailed error information
            const errorDetails = {
                status: xhr.status,
                statusText: xhr.statusText,
                readyState: xhr.readyState,
                responseText: xhr.responseText || 'No response'
            };
            console.error('❌ XHR Network Error:', errorDetails);

            // Send to backend for logging
            fetch('/api/log-client-error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    error_type: 'xhr_network_error',
                    details: errorDetails,
                    user_id: userId
                })
            }).catch(() => {});

            reject(new Error(`Network error: ${xhr.status} ${xhr.statusText}`));
        });

        // B2 Native API requires specific headers
        xhr.open('POST', uploadData.upload_url);
        xhr.setRequestHeader('Authorization', uploadData.authorization_token);
        xhr.setRequestHeader('X-Bz-File-Name', encodeURIComponent(uploadData.object_key));
        xhr.setRequestHeader('Content-Type', uploadData.content_type);
        xhr.setRequestHeader('X-Bz-Content-Sha1', 'do_not_verify'); // Skip SHA1 verification for speed

        console.log('📤 Uploading to B2 Native API:', {
            url: uploadData.upload_url,
            fileName: uploadData.object_key,
            contentType: uploadData.content_type
        });

        xhr.send(file);
    });
}

// Notify Backend Upload Complete
async function notifyUploadComplete(objectKey, fileName, fileSize, previewUrl = null) {
    console.log('📢 Notifying server...');

    const payload = {
        object_key: objectKey,
        file_name: fileName,
        file_size: fileSize,
        user_id: userId,
        telegram_init_data: tg.initData
    };

    // Add preview URL if generated (PDF only)
    if (previewUrl) {
        payload.preview_url = previewUrl;
        console.log('📸 Sending preview URL:', previewUrl);
    }

    const response = await fetch('/api/upload-complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.detail || `HTTP ${response.status}`;
        console.error('❌ Failed to notify completion:', errorMsg);
        throw new Error(`Erreur notification: ${errorMsg}`);
    }

    console.log('✅ Server notified');
}

// UI State Management
function showSuccess() {
    progressSection.classList.add('hidden');
    successSection.classList.remove('hidden');
}

function showError(message) {
    uploadArea.classList.add('hidden');
    progressSection.classList.add('hidden');
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;
}

// Helper: Format bytes to human readable
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
