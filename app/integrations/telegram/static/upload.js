// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Vérifier que l'app est bien dans Telegram
if (!tg.initData || tg.initData.length === 0) {
    console.error('❌ Not running in Telegram WebApp or initData is empty');
    document.body.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <h2>⚠️ Erreur</h2>
            <p>Cette application doit être ouverte depuis Telegram.</p>
            <p>Utilisez le bouton "📤 Upload via Mini App" dans le bot.</p>
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

// Handle File Selection
async function handleFileSelection(file) {
    console.log('File selected:', file.name, formatBytes(file.size));

    // Validation
    const maxSize = 10 * 1024 * 1024 * 1024; // 10 GB
    if (file.size > maxSize) {
        showError('Fichier trop volumineux (max 10 GB)');
        return;
    }

    // Update UI
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);

    uploadArea.classList.add('hidden');
    progressSection.classList.remove('hidden');

    // Request Presigned Upload URL
    try {
        const presignedData = await requestPresignedUploadURL(file.name, file.type, userId);

        if (!presignedData || !presignedData.upload_url) {
            throw new Error('Failed to get upload URL');
        }

        // Upload to B2
        await uploadFileToB2(file, presignedData.upload_url, presignedData.object_key);

        // Notify backend upload complete
        await notifyUploadComplete(presignedData.object_key, file.name, file.size);

        // Show success
        showSuccess();

    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message || 'Erreur lors de l\'upload');
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

// Upload File to B2 via Presigned URL
async function uploadFileToB2(file, uploadUrl, objectKey) {
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
                resolve();
            } else {
                reject(new Error('Upload failed: ' + xhr.status));
            }
        });

        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });

        xhr.open('PUT', uploadUrl);
        xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
        xhr.send(file);
    });
}

// Notify Backend Upload Complete
async function notifyUploadComplete(objectKey, fileName, fileSize) {
    console.log('📢 Notifying server...');

    const response = await fetch('/api/upload-complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            object_key: objectKey,
            file_name: fileName,
            file_size: fileSize,
            user_id: userId,
            telegram_init_data: tg.initData
        })
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
