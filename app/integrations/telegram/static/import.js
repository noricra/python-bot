// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Verifier execution dans Telegram WebApp
if (!tg.initData || tg.initData.length === 0) {
    console.error('[IMPORT] Not running in Telegram WebApp');
    document.body.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <h2>Erreur</h2>
            <p>Cette application doit etre ouverte depuis Telegram.</p>
            <p>Utilisez le bouton d'import dans le bot.</p>
        </div>
    `;
    throw new Error('Not in Telegram WebApp');
}

// Configure PDF.js worker
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

// Get user data
const userId = tg.initDataUnsafe?.user?.id;
const urlParams = new URLSearchParams(window.location.search);
const userLang = urlParams.get('lang') || 'fr';

// Translations
const translations = {
    fr: {
        loading: 'Chargement des produits...',
        noProducts: 'Aucun produit a importer',
        fileTooLarge: 'Fichier trop volumineux (max 10 GB)',
        invalidPDF: 'Fichier PDF invalide ou corrompu',
        pdfValidationError: 'Impossible de valider le PDF',
        preparing: 'Preparation...',
        generatingPreview: 'Generation apercu...',
        uploadingPreview: 'Upload apercu...',
        importSuccess: 'Importe avec succes',
        importError: 'Erreur lors de l\'import',
        skipped: 'Produit passe',
        uploadInProgress: 'Upload en cours. Etes-vous sur de vouloir quitter?',
        category: 'Categorie',
        categoryHint: 'Modifiez si la categorie automatique est incorrecte'
    },
    en: {
        loading: 'Loading products...',
        noProducts: 'No products to import',
        fileTooLarge: 'File too large (max 10 GB)',
        invalidPDF: 'Invalid or corrupted PDF file',
        pdfValidationError: 'Unable to validate PDF',
        preparing: 'Preparing...',
        generatingPreview: 'Generating preview...',
        uploadingPreview: 'Uploading preview...',
        importSuccess: 'Imported successfully',
        importError: 'Import error',
        skipped: 'Product skipped',
        uploadInProgress: 'Upload in progress. Are you sure you want to leave?',
        category: 'Category',
        categoryHint: 'Change if auto-category is incorrect'
    }
};

// Translation helper
const t = (key) => translations[userLang][key] || translations['fr'][key];

console.log('[IMPORT] Telegram WebApp initialized');
console.log('[IMPORT] User ID:', userId);

// State
let products = [];
let currentIndex = 0;
let results = {
    imported: 0,
    skipped: 0,
    errors: 0
};
let availableCategories = [];

// DOM Elements
const loadingSection = document.getElementById('loadingSection');
const carouselSection = document.getElementById('carouselSection');
const summarySection = document.getElementById('summarySection');
const errorSection = document.getElementById('errorSection');
const progressSection = document.getElementById('progressSection');

const productImage = document.getElementById('productImage');
const productTitle = document.getElementById('productTitle');
const productCategory = document.getElementById('productCategory');
const productRating = document.getElementById('productRating');
const productPrice = document.getElementById('productPrice');
const productDescription = document.getElementById('productDescription');
const uploadStatus = document.getElementById('uploadStatus');

const currentIndexEl = document.getElementById('currentIndex');
const totalProductsEl = document.getElementById('totalProducts');

const btnUpload = document.getElementById('btnUpload');
const btnSkip = document.getElementById('btnSkip');
const btnPrev = document.getElementById('btnPrev');
const btnNext = document.getElementById('btnNext');
const fileInput = document.getElementById('fileInput');

const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const uploadSpeed = document.getElementById('uploadSpeed');
const fileName = document.getElementById('fileName');

// Initialize
async function init() {
    try {
        // Load categories first
        console.log('[IMPORT] Fetching categories...');
        try {
            const catResponse = await fetch('/api/categories');
            if (catResponse.ok) {
                const catData = await catResponse.json();
                availableCategories = catData.categories || [];
                console.log('[IMPORT] Loaded categories:', availableCategories);
            }
        } catch (e) {
            console.warn('[IMPORT] Failed to load categories:', e);
            availableCategories = ['Autre'];
        }

        console.log('[IMPORT] Fetching products...');

        const response = await fetch(`/api/import-products?user_id=${userId}`, {
            headers: {
                'X-Telegram-Init-Data': tg.initData
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch products');
        }

        const data = await response.json();
        products = data.products || [];

        console.log(`[IMPORT] Loaded ${products.length} products`);

        if (products.length === 0) {
            showError(t('noProducts'));
            return;
        }

        loadingSection.classList.add('hidden');
        carouselSection.classList.remove('hidden');
        totalProductsEl.textContent = products.length;

        displayProduct(0);

        btnUpload.addEventListener('click', handleUploadClick);
        btnSkip.addEventListener('click', handleSkip);
        btnPrev.addEventListener('click', () => navigateTo(currentIndex - 1));
        btnNext.addEventListener('click', () => navigateTo(currentIndex + 1));
        fileInput.addEventListener('change', handleFileSelected);

    } catch (error) {
        console.error('[IMPORT] Init error:', error);
        showError(error.message);
    }
}

// Display product
function displayProduct(index) {
    if (index < 0 || index >= products.length) {
        return;
    }

    currentIndex = index;
    const product = products[index];

    console.log(`[IMPORT] Displaying product ${index + 1}/${products.length}:`, product.title);

    currentIndexEl.textContent = index + 1;

    const imageUrl = product.cover_image_url || product.image_url;
    if (imageUrl) {
        productImage.src = imageUrl;
        productImage.style.display = 'block';
    } else {
        productImage.style.display = 'none';
    }

    productTitle.textContent = product.title;

    // Category dropdown
    productCategory.innerHTML = '';
    const categoryLabel = document.createElement('label');
    categoryLabel.textContent = t('category') + ': ';
    categoryLabel.style.cssText = 'font-weight: 600; margin-right: 8px;';

    const categorySelect = document.createElement('select');
    categorySelect.style.cssText = 'padding: 6px 10px; border: 2px solid #e0e0e0; border-radius: 6px; font-size: 14px; background: white; min-width: 150px;';
    categorySelect.required = true;

    // DEBUG: Vérifier si categories chargées
    if (availableCategories.length === 0) {
        console.error('[IMPORT] No categories available! Using fallback.');
        availableCategories = ['Autre'];
    }

    console.log(`[IMPORT] Building dropdown with ${availableCategories.length} categories`);

    availableCategories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        option.selected = (cat === product.category);
        categorySelect.appendChild(option);
    });

    // Si product.category n'est pas dans la liste, sélectionner la première
    if (!product.category || !availableCategories.includes(product.category)) {
        product.category = availableCategories[0];
        categorySelect.value = availableCategories[0];
        console.log(`[IMPORT] No valid category, defaulting to: ${product.category}`);
    }

    categorySelect.addEventListener('change', (e) => {
        product.category = e.target.value;
        console.log(`[IMPORT] Category changed to: ${product.category}`);
    });

    productCategory.appendChild(categoryLabel);
    productCategory.appendChild(categorySelect);

    if (product.rating > 0) {
        const stars = Array(Math.round(product.rating)).fill('*').join('');
        productRating.textContent = `${stars} ${product.rating.toFixed(1)}`;
    } else {
        productRating.textContent = '';
    }

    const price = product.price || 0;
    productPrice.textContent = price > 0 ? `$${price.toFixed(2)}` : 'Gratuit';

    productDescription.textContent = product.description || 'Pas de description';

    btnPrev.disabled = index === 0;
    btnNext.disabled = index === products.length - 1;

    if (product.status) {
        showStatus(product.status, product.statusMessage);
        btnUpload.disabled = product.status === 'imported';
        btnSkip.disabled = product.status === 'imported';
    } else {
        uploadStatus.classList.add('hidden');
        btnUpload.disabled = false;
        btnSkip.disabled = false;
    }
}

// Navigate
function navigateTo(index) {
    if (index < 0 || index >= products.length) {
        return;
    }
    displayProduct(index);
}

// Handle Upload Click
function handleUploadClick() {
    fileInput.click();
}

// Generate PDF Preview (copied from upload.js)
async function generatePDFPreview(file) {
    try {
        console.log('[IMPORT] Generating PDF preview...');

        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        console.log(`[IMPORT] PDF loaded: ${pdf.numPages} pages`);

        const page = await pdf.getPage(1);
        const viewport = page.getViewport({ scale: 2.0 });

        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = viewport.width;
        canvas.height = viewport.height;

        await page.render({
            canvasContext: context,
            viewport: viewport
        }).promise;

        console.log('[IMPORT] PDF preview rendered to canvas');

        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                console.log(`[IMPORT] Preview PNG generated: ${formatBytes(blob.size)}`);
                resolve(blob);
            }, 'image/png', 0.9);
        });
    } catch (error) {
        console.error('[IMPORT] PDF preview generation failed:', error);
        return null;
    }
}

// Get B2 upload URL for a specific path (for preview)
async function getB2UploadUrlForPath(objectKey, contentType) {
    console.log('[IMPORT] Requesting B2 URL for path:', objectKey);

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
        console.error('[IMPORT] Failed to get B2 upload URL for path');
        return null;
    }

    const data = await response.json();
    console.log('[IMPORT] B2 upload URL received for path');
    return data;
}

// Handle File Selected (SAME TECH AS upload.js)
async function handleFileSelected(e) {
    const file = e.target.files[0];
    if (!file) return;

    console.log('[IMPORT] File selected:', file.name, formatBytes(file.size));

    const product = products[currentIndex];

    const maxSize = 10 * 1024 * 1024 * 1024; // 10 GB
    if (file.size > maxSize) {
        showStatus('error', t('fileTooLarge'));
        return;
    }

    // Validation PDF integrity
    const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

    if (isPDF) {
        // Verifier magic bytes (%PDF)
        try {
            const buffer = await file.slice(0, 4).arrayBuffer();
            const header = new Uint8Array(buffer);

            if (header[0] !== 0x25 || header[1] !== 0x50 ||
                header[2] !== 0x44 || header[3] !== 0x46) {
                showStatus('error', t('invalidPDF'));
                resetUploadUI();
                fileInput.value = '';
                return;
            }
        } catch (error) {
            console.error('[IMPORT] PDF validation error:', error);
            showStatus('error', t('pdfValidationError'));
            resetUploadUI();
            fileInput.value = '';
            return;
        }
    }

    btnUpload.disabled = true;
    btnSkip.disabled = true;
    btnPrev.disabled = true;
    btnNext.disabled = true;

    setupUploadGuard(true);

    carouselSection.querySelector('.product-card').style.display = 'none';
    progressSection.classList.remove('hidden');
    fileName.textContent = file.name;

    try {
        // 1. Request main file upload URL (generates product_id)
        progressPercent.textContent = t('preparing');
        const uploadData = await requestPresignedUploadURL(file.name, file.type, userId);

        if (!uploadData || !uploadData.upload_url || !uploadData.product_id) {
            throw new Error('Failed to get upload URL or product_id');
        }

        const productId = uploadData.product_id;
        console.log('[IMPORT] Product ID received:', productId);

        // 2. If PDF, generate and upload preview (uses product_id)
        let previewUrl = null;
        const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

        if (isPDF) {
            try {
                console.log('[IMPORT] PDF detected, generating preview...');
                progressPercent.textContent = t('generatingPreview');

                const previewBlob = await generatePDFPreview(file);

                if (previewBlob) {
                    console.log('[IMPORT] Uploading preview to B2...');
                    progressPercent.textContent = t('uploadingPreview');

                    const previewObjectKey = `products/${userId}/${productId}/preview.png`;
                    console.log('[IMPORT] Preview path:', previewObjectKey);

                    const b2 = await getB2UploadUrlForPath(previewObjectKey, 'image/png');

                    if (b2) {
                        await uploadFileToB2(previewBlob, b2);
                        previewUrl = `https://s3.us-west-004.backblazeb2.com/${previewObjectKey}`;
                        console.log('[IMPORT] Preview uploaded:', previewUrl);
                    }
                }
            } catch (error) {
                console.warn('[IMPORT] Preview generation failed, continuing without preview:', error);
            }
        }

        // 3. Upload main file
        progressPercent.textContent = '0%';
        console.log('[IMPORT] Uploading main file to:', uploadData.object_key);
        await uploadFileToB2(file, uploadData);

        // 4. Notify backend
        await notifyImportComplete(uploadData.object_key, file.name, file.size, previewUrl, product);

        // Success
        product.status = 'imported';
        product.statusMessage = t('importSuccess');
        results.imported++;

        setupUploadGuard(false);

        showStatus('success', t('importSuccess'));

        setTimeout(() => {
            if (currentIndex < products.length - 1) {
                navigateTo(currentIndex + 1);
                resetUploadUI();
            } else {
                showSummary();
            }
        }, 1500);

    } catch (error) {
        console.error('[IMPORT] Upload error:', error);
        product.status = 'error';
        product.statusMessage = `${t('importError')}: ${error.message}`;
        results.errors++;

        setupUploadGuard(false);

        showStatus('error', `${t('importError')}: ${error.message}`);
        resetUploadUI();
    }

    fileInput.value = '';
}

// Handle Skip
function handleSkip() {
    const product = products[currentIndex];
    product.status = 'skipped';
    product.statusMessage = t('skipped');
    results.skipped++;

    console.log(`[IMPORT] Skipped product: ${product.title}`);

    showStatus('skipped', t('skipped'));

    setTimeout(() => {
        if (currentIndex < products.length - 1) {
            navigateTo(currentIndex + 1);
        } else {
            showSummary();
        }
    }, 500);
}

// Request Presigned URL
async function requestPresignedUploadURL(fileName, fileType, userId) {
    console.log('[IMPORT] Requesting presigned URL...');

    const response = await fetch('/api/generate-upload-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            file_name: fileName,
            file_type: fileType,
            user_id: userId,
            telegram_init_data: tg.initData
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.detail || `HTTP ${response.status}`;
        console.error('[IMPORT] Failed to get upload URL:', errorMsg);
        throw new Error(`Erreur serveur: ${errorMsg}`);
    }

    const data = await response.json();
    console.log('[IMPORT] Presigned URL received');
    return data;
}

// Upload File to B2
async function uploadFileToB2(file, uploadData) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        let startTime = Date.now();
        let lastLoaded = 0;

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                progressBar.style.width = percent + '%';
                progressPercent.textContent = Math.round(percent) + '%';

                const elapsed = (Date.now() - startTime) / 1000;
                const speed = (e.loaded - lastLoaded) / elapsed / (1024 * 1024);
                uploadSpeed.textContent = speed.toFixed(2) + ' MB/s';

                lastLoaded = e.loaded;
                startTime = Date.now();
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                console.log('[IMPORT] Upload successful to B2');
                resolve();
            } else {
                const errorDetails = {
                    status: xhr.status,
                    statusText: xhr.statusText,
                    responseText: xhr.responseText || 'No response'
                };
                console.error('[IMPORT] Upload HTTP Error:', errorDetails);

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
            const errorDetails = {
                status: xhr.status,
                statusText: xhr.statusText,
                readyState: xhr.readyState,
                responseText: xhr.responseText || 'No response'
            };
            console.error('[IMPORT] XHR Network Error:', errorDetails);

            fetch('/api/log-client-error', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    error_type: 'xhr_network_error',
                    details: errorDetails,
                    user_id: userId
                })
            }).catch(() => {});

            reject(new Error(`Network error during upload`));
        });

        xhr.open('PUT', uploadData.upload_url);
        xhr.setRequestHeader('Content-Type', uploadData.content_type);

        console.log('[IMPORT] Uploading to B2 via S3 presigned URL:', {
            method: 'PUT',
            contentType: uploadData.content_type,
            fileSize: formatBytes(file.size)
        });

        xhr.send(file);
    });
}

// Notify Backend Import Complete
async function notifyImportComplete(objectKey, fileName, fileSize, previewUrl, product) {
    console.log('[IMPORT] Notifying server...');

    const payload = {
        object_key: objectKey,
        file_name: fileName,
        file_size: fileSize,
        user_id: userId,
        telegram_init_data: tg.initData,
        product_metadata: {
            title: product.title,
            description: product.description,
            price: product.price,
            category: product.category,
            imported_from: 'gumroad',
            imported_url: product.gumroad_url,
            cover_image_url: product.cover_image_url || product.image_url
        }
    };

    if (previewUrl) {
        payload.preview_url = previewUrl;
        console.log('[IMPORT] Sending preview URL:', previewUrl);
    }

    const response = await fetch('/api/import-complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.detail || `HTTP ${response.status}`;
        console.error('[IMPORT] Failed to notify completion:', errorMsg);
        throw new Error(`Erreur notification: ${errorMsg}`);
    }

    console.log('[IMPORT] Server notified successfully');
}

// Show Status
function showStatus(type, message) {
    uploadStatus.classList.remove('hidden', 'status-success', 'status-error', 'status-skipped');

    if (type === 'success') {
        uploadStatus.classList.add('status-success');
    } else if (type === 'error') {
        uploadStatus.classList.add('status-error');
    } else if (type === 'skipped') {
        uploadStatus.classList.add('status-skipped');
    }

    uploadStatus.textContent = message;
}

// Reset Upload UI
function resetUploadUI() {
    progressSection.classList.add('hidden');
    carouselSection.querySelector('.product-card').style.display = 'block';
    progressBar.style.width = '0%';
    progressPercent.textContent = '0%';
    uploadSpeed.textContent = '0 MB/s';

    btnPrev.disabled = currentIndex === 0;
    btnNext.disabled = currentIndex === products.length - 1;
}

// Show Summary
function showSummary() {
    console.log('[IMPORT] Showing summary:', results);

    carouselSection.classList.add('hidden');
    summarySection.classList.remove('hidden');

    document.getElementById('importedCount').textContent = results.imported;
    document.getElementById('skippedCount').textContent = results.skipped;
    document.getElementById('errorCount').textContent = results.errors;
}

// Show Error
function showError(message) {
    loadingSection.classList.add('hidden');
    carouselSection.classList.add('hidden');
    errorSection.classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
}

// Helper: Format bytes
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Setup Upload Guard
function setupUploadGuard(enabled) {
    if (enabled) {
        window.onbeforeunload = () => t('uploadInProgress');
    } else {
        window.onbeforeunload = null;
    }
}

// Start
init();
