/**
 * RationSmart - Progressive Web App (PWA) Manager & Offline Sync Engine
 * IndexedDB database: RationSmartPWA (v1)
 * Stores: sales, stock, pendingQueue, cards
 */

const PWA_DB_NAME = 'RationSmartPWA';
const PWA_DB_VERSION = 1;

class RationSmartPWA {
    constructor() {
        this.db = null;
        this.deferredInstallPrompt = null;
        this.devOfflineSimulation = localStorage.getItem('pwa_dev_offline_sim') === 'true';
        this.isSyncing = false;
        this.init();
    }

    async init() {
        try {
            await this.openDatabase();
            this.registerServiceWorker();
            this.setupInstallPrompt();
            this.setupNetworkMonitoring();
            this.setupDevSimulation();
            this.updatePendingCount();

            // Auto-cache stock & cards if online and on dealer workstation
            if (this.isOnline()) {
                this.bootstrapDealerCache();
                // Attempt automatic background sync of any previously pending sales
                setTimeout(() => this.syncPendingSales(), 2000);
            }
        } catch (err) {
            console.error('[PWA] Initialization error:', err);
        }
    }

    // =========================================================================
    // 1. IndexedDB Management
    // =========================================================================

    openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(PWA_DB_NAME, PWA_DB_VERSION);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // 1. sales store
                if (!db.objectStoreNames.contains('sales')) {
                    const salesStore = db.createObjectStore('sales', { keyPath: 'clientSaleId' });
                    salesStore.createIndex('syncStatus', 'syncStatus', { unique: false });
                    salesStore.createIndex('cardNumber', 'cardNumber', { unique: false });
                    salesStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // 2. stock store (local shop stock cache)
                if (!db.objectStoreNames.contains('stock')) {
                    const stockStore = db.createObjectStore('stock', { keyPath: 'commodityId' });
                    stockStore.createIndex('itemName', 'itemName', { unique: false });
                }

                // 3. pendingQueue store (FIFO synchronization queue)
                if (!db.objectStoreNames.contains('pendingQueue')) {
                    const queueStore = db.createObjectStore('pendingQueue', { keyPath: 'operationId' });
                    queueStore.createIndex('clientSaleId', 'clientSaleId', { unique: true });
                    queueStore.createIndex('createdAt', 'createdAt', { unique: false });
                }

                // 4. cards store (cached minimal card entitlement records for assigned shop)
                if (!db.objectStoreNames.contains('cards')) {
                    const cardsStore = db.createObjectStore('cards', { keyPath: 'cardNumber' });
                    cardsStore.createIndex('headOfFamily', 'headOfFamily', { unique: false });
                    cardsStore.createIndex('aadhaarLast4', 'aadhaarLast4', { unique: false });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };

            request.onerror = (event) => {
                console.error('[PWA] IndexedDB error:', event.target.error);
                reject(event.target.error);
            };
        });
    }

    getStore(storeName, mode = 'readonly') {
        const tx = this.db.transaction(storeName, mode);
        return tx.objectStore(storeName);
    }

    // =========================================================================
    // 2. Service Worker Registration & Installability
    // =========================================================================

    registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then((registration) => {
                    // Check for background sync support
                    if ('sync' in registration) {
                        navigator.serviceWorker.addEventListener('message', (event) => {
                            if (event.data && event.data.type === 'PWA_TRIGGER_BACKGROUND_SYNC') {
                                this.syncPendingSales();
                            }
                        });
                    }
                })
                .catch((err) => {
                    console.warn('[PWA] SW registration failed:', err);
                });
        }
    }

    setupInstallPrompt() {
        const installBtn = document.getElementById('pwaInstallBtn');
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredInstallPrompt = e;
            if (installBtn) {
                installBtn.classList.remove('d-none');
                installBtn.addEventListener('click', async () => {
                    if (this.deferredInstallPrompt) {
                        this.deferredInstallPrompt.prompt();
                        const { outcome } = await this.deferredInstallPrompt.userChoice;
                        if (outcome === 'accepted') {
                            installBtn.classList.add('d-none');
                        }
                        this.deferredInstallPrompt = null;
                    }
                });
            }
        });

        window.addEventListener('appinstalled', () => {
            if (installBtn) installBtn.classList.add('d-none');
            this.deferredInstallPrompt = null;
        });
    }

    // =========================================================================
    // 3. Network Connection & Offline Banner Monitoring
    // =========================================================================

    isOnline() {
        if (this.devOfflineSimulation) return false;
        return navigator.onLine;
    }

    setupNetworkMonitoring() {
        window.addEventListener('online', () => {
            this.updateConnectionUI();
            this.bootstrapDealerCache();
            this.syncPendingSales();
        });

        window.addEventListener('offline', () => {
            this.updateConnectionUI();
        });

        this.updateConnectionUI();
    }

    updateConnectionUI() {
        const statusEl = document.getElementById('pwaConnectionStatus');
        const offlineBanner = document.getElementById('pwaOfflineBanner');
        const syncNowBtn = document.getElementById('btnPwaSyncNow');
        const online = this.isOnline();

        if (statusEl) {
            if (online) {
                statusEl.innerHTML = `
                    <span class="pds-status-dot online"></span>
                    <span class="pds-status-text">Online</span>
                `;
                statusEl.className = 'pds-connection-pill online';
                statusEl.setAttribute('title', 'System connected to district PDS central server');
            } else {
                const isSimulated = this.devOfflineSimulation ? ' (Simulation)' : '';
                statusEl.innerHTML = `
                    <span class="pds-status-dot offline"></span>
                    <span class="pds-status-text">Offline${isSimulated}</span>
                `;
                statusEl.className = 'pds-connection-pill offline';
                statusEl.setAttribute('title', 'Working offline. Sales will be saved locally in IndexedDB.');
            }
        }

        if (offlineBanner) {
            if (!online) {
                offlineBanner.classList.remove('d-none');
            } else {
                offlineBanner.classList.add('d-none');
            }
        }

        const exitSimBtn = document.getElementById('btnExitOfflineSim');
        const modeBadge = document.getElementById('pwaOfflineModeBadge');

        if (exitSimBtn) {
            if (this.devOfflineSimulation) {
                exitSimBtn.classList.remove('d-none');
            } else {
                exitSimBtn.classList.add('d-none');
            }
        }

        if (modeBadge) {
            modeBadge.innerText = this.devOfflineSimulation ? 'OFFLINE (SIMULATION)' : 'OFFLINE MODE';
        }

        if (syncNowBtn) {
            syncNowBtn.disabled = !online || this.isSyncing;
        }

        // Update any POS offline labels if present on POS page
        this.updatePosOfflineIndicators();
    }

    updatePosOfflineIndicators() {
        const posIndicator = document.getElementById('posOfflineModeIndicator');
        const posExitSimBtn = document.getElementById('btnPosExitSim');
        const stockBadges = document.querySelectorAll('.pos-stock-offline-badge');
        const online = this.isOnline();

        if (posIndicator) {
            if (!online) {
                posIndicator.classList.remove('d-none');
            } else {
                posIndicator.classList.add('d-none');
            }
        }

        if (posExitSimBtn) {
            if (this.devOfflineSimulation) {
                posExitSimBtn.classList.remove('d-none');
            } else {
                posExitSimBtn.classList.add('d-none');
            }
        }

        stockBadges.forEach((el) => {
            if (!online) {
                el.classList.remove('d-none');
            } else {
                el.classList.add('d-none');
            }
        });
    }

    setupDevSimulation() {
        const simToggle = document.getElementById('devOfflineSimulationToggle');
        if (simToggle) {
            simToggle.checked = this.devOfflineSimulation;
            simToggle.addEventListener('change', (e) => {
                this.setDevOffline(e.target.checked);
            });
        }
    }

    async setDevOffline(enabled) {
        if (enabled && navigator.onLine) {
            // Pre-cache before simulating offline to ensure offline card lookups work smoothly
            try {
                await this.bootstrapDealerCache();
            } catch (err) {
                console.warn('[PWA] Bootstrap cache warning:', err);
            }
        }

        this.devOfflineSimulation = Boolean(enabled);
        localStorage.setItem('pwa_dev_offline_sim', this.devOfflineSimulation ? 'true' : 'false');

        const simToggle = document.getElementById('devOfflineSimulationToggle');
        if (simToggle) {
            simToggle.checked = this.devOfflineSimulation;
        }

        this.updateConnectionUI();

        // Switched back to online: auto-sync pending sales
        if (!this.devOfflineSimulation && navigator.onLine) {
            this.bootstrapDealerCache();
            setTimeout(() => this.syncPendingSales(), 500);
        }
    }

    // =========================================================================
    // 4. Dealer Data Caching (Stock & Assigned Cards)
    // =========================================================================

    async bootstrapDealerCache() {
        // Only run for authenticated dealers with an assigned shop
        try {
            const res = await fetch('/api/dealer/pwa-bootstrap', {
                headers: { 'Accept': 'application/json' }
            });

            if (!res.ok) {
                // If not authenticated as dealer or error, exit silently
                return;
            }

            const data = await res.json();
            if (data && data.success) {
                // 1. Cache commodities & stock
                if (data.stock && Array.isArray(data.stock)) {
                    await this.saveLocalStock(data.stock);
                }

                // 2. Cache cardholder records for dealer's shop
                if (data.cards && Array.isArray(data.cards)) {
                    await this.saveLocalCards(data.cards);
                }

                localStorage.setItem('pwa_last_bootstrap', new Date().toISOString());
                localStorage.setItem('pwa_shop_info', JSON.stringify(data.shop || {}));
            }
        } catch (err) {
            // Network fetch failure is expected when offline
        }
    }

    saveLocalStock(stockList) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction('stock', 'readwrite');
            const store = tx.objectStore('stock');
            stockList.forEach((item) => {
                store.put({
                    commodityId: item.commodity_id,
                    code: item.code,
                    name: item.name,
                    itemName: item.name,
                    unit: item.unit,
                    unitPrice: item.unit_price,
                    currentStock: parseFloat(item.current_stock) || 0,
                    minThreshold: parseFloat(item.min_threshold) || 100,
                    lastUpdated: new Date().toISOString()
                });
            });
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }

    saveLocalCards(cardList) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction('cards', 'readwrite');
            const store = tx.objectStore('cards');
            cardList.forEach((card) => {
                store.put({
                    id: card.id,
                    cardNumber: card.card_number,
                    headOfFamily: card.head_of_family,
                    cardType: card.card_type,
                    membersCount: card.members_count,
                    aadhaarLast4: card.aadhaar_last4,
                    mobile: card.mobile,
                    assignedShopId: card.assigned_shop_id,
                    status: card.status,
                    quotaItems: card.quota_items || [],
                    monthPeriod: card.month_period
                });
            });
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }

    async getLocalStock(commodityId) {
        return new Promise((resolve, reject) => {
            const store = this.getStore('stock');
            const req = store.get(commodityId);
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async getAllLocalStock() {
        return new Promise((resolve, reject) => {
            const store = this.getStore('stock');
            const req = store.getAll();
            req.onsuccess = () => resolve(req.result || []);
            req.onerror = () => reject(req.error);
        });
    }

    async lookupCardOffline(query) {
        if (!query) return null;
        const q = query.trim().toUpperCase();
        return new Promise((resolve, reject) => {
            const store = this.getStore('cards');
            const req = store.getAll();
            req.onsuccess = () => {
                const cards = req.result || [];
                const matched = cards.find(c => 
                    c.cardNumber.toUpperCase() === q ||
                    (c.mobile && c.mobile === q) ||
                    (c.aadhaarLast4 && c.aadhaarLast4 === q)
                );
                resolve(matched || null);
            };
            req.onerror = () => reject(req.error);
        });
    }

    // =========================================================================
    // 5. Offline Sale Submission & Local Stock Deduction
    // =========================================================================

    async recordOfflineSale(saleData) {
        // 1. Generate unique clientSaleId (Idempotency Key)
        const dateStr = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
        const randomHex = Math.random().toString(36).substring(2, 8).toUpperCase();
        const clientSaleId = `OFFLINE-${dateStr}-${randomHex}`;

        // 2. Validate against local cached stock to prevent negative inventory
        for (const item of saleData.items) {
            const stockRecord = await this.getLocalStock(item.commodityId);
            if (stockRecord) {
                if (item.quantity > stockRecord.currentStock) {
                    throw new Error(`Insufficient offline stock for ${stockRecord.name}. Available: ${stockRecord.currentStock} ${stockRecord.unit}, Requested: ${item.quantity} ${stockRecord.unit}`);
                }
            }
        }

        // 3. Deduct stock locally in IndexedDB stock store
        const stockTx = this.db.transaction('stock', 'readwrite');
        const stockStore = stockTx.objectStore('stock');
        for (const item of saleData.items) {
            const stockRecord = await new Promise((res) => {
                const req = stockStore.get(item.commodityId);
                req.onsuccess = () => res(req.result);
            });
            if (stockRecord) {
                stockRecord.currentStock = Math.max(0, Math.round((stockRecord.currentStock - item.quantity) * 100) / 100);
                stockRecord.lastUpdated = new Date().toISOString();
                stockStore.put(stockRecord);
            }
        }

        // 4. Update local card remaining quota so repeated offline billing cannot exceed quota
        if (saleData.cardNumber) {
            const cardTx = this.db.transaction('cards', 'readwrite');
            const cardStore = cardTx.objectStore('cards');
            const card = await new Promise((res) => {
                const req = cardStore.get(saleData.cardNumber);
                req.onsuccess = () => res(req.result);
            });
            if (card && card.quotaItems) {
                saleData.items.forEach((item) => {
                    const qItem = card.quotaItems.find(qi => qi.commodity_id === item.commodityId);
                    if (qItem) {
                        qItem.claimed_qty = (qItem.claimed_qty || 0) + item.quantity;
                        qItem.remaining_qty = Math.max(0, (qItem.remaining_qty || 0) - item.quantity);
                    }
                });
                cardStore.put(card);
            }
        }

        // 5. Construct full local sale record
        const saleRecord = {
            clientSaleId,
            cardNumber: saleData.cardNumber,
            headOfFamily: saleData.headOfFamily || 'Beneficiary',
            cardType: saleData.cardType || 'PHH',
            shopId: saleData.shopId,
            items: saleData.items,
            totalAmount: saleData.totalAmount,
            authMode: saleData.authMode || 'Biometric Aadhaar (Offline Verified)',
            paymentMode: saleData.paymentMode || 'Cash / Direct Subsidy',
            timestamp: new Date().toISOString(),
            synced: false,
            syncStatus: 'pending', // 'pending' | 'synced' | 'rejected'
            errorMessage: null,
            billNumber: null,
            serverTransactionId: null
        };

        // 6. Save in sales store and pendingQueue store in a single transaction
        await new Promise((resolve, reject) => {
            const tx = this.db.transaction(['sales', 'pendingQueue'], 'readwrite');
            const salesStore = tx.objectStore('sales');
            const queueStore = tx.objectStore('pendingQueue');

            salesStore.put(saleRecord);
            queueStore.put({
                operationId: `OP-${clientSaleId}`,
                type: 'sale',
                clientSaleId,
                payload: saleRecord,
                createdAt: new Date().toISOString(),
                retryCount: 0
            });

            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });

        this.updatePendingCount();
        return saleRecord;
    }

    // =========================================================================
    // 6. Server Synchronization Engine (Idempotent Bulk Sync)
    // =========================================================================

    async syncPendingSales() {
        if (!this.isOnline() || this.isSyncing) return { status: 'skipped' };

        this.isSyncing = true;
        this.updateConnectionUI();

        const syncBtn = document.getElementById('btnPwaSyncNow');
        if (syncBtn) {
            syncBtn.disabled = true;
            syncBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Syncing...';
        }

        try {
            // 1. Gather all pending items from pendingQueue
            const queueItems = await new Promise((resolve, reject) => {
                const store = this.getStore('pendingQueue');
                const req = store.getAll();
                req.onsuccess = () => resolve(req.result || []);
                req.onerror = () => reject(req.error);
            });

            if (queueItems.length === 0) {
                this.isSyncing = false;
                if (syncBtn) {
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = '<i class="bi bi-check-all me-1"></i> Synced';
                    setTimeout(() => {
                        syncBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i> Sync Now';
                    }, 2000);
                }
                this.updatePendingCount();
                return { status: 'no_pending' };
            }

            // 2. Prepare payload for /api/sales/bulk-sync
            const salesPayload = queueItems.map(item => item.payload);

            const response = await fetch('/api/sales/bulk-sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ sales: salesPayload })
            });

            if (!response.ok) {
                throw new Error(`Server returned status ${response.status}`);
            }

            const result = await response.json();

            // 3. Process outcomes atomically in local stores
            const tx = this.db.transaction(['sales', 'pendingQueue'], 'readwrite');
            const salesStore = tx.objectStore('sales');
            const queueStore = tx.objectStore('pendingQueue');

            // Handle accepted sales
            if (result.synced && Array.isArray(result.synced)) {
                for (const syn of result.synced) {
                    const existingSale = await new Promise((res) => {
                        const req = salesStore.get(syn.clientSaleId);
                        req.onsuccess = () => res(req.result);
                    });
                    if (existingSale) {
                        existingSale.synced = true;
                        existingSale.syncStatus = 'synced';
                        existingSale.billNumber = syn.billNumber;
                        existingSale.serverTransactionId = syn.transactionId;
                        existingSale.totalAmount = syn.totalAmount || existingSale.totalAmount;
                        existingSale.errorMessage = null;
                        salesStore.put(existingSale);
                    }
                    queueStore.delete(`OP-${syn.clientSaleId}`);
                }
            }

            // Handle already-processed sales (Idempotency confirmation)
            if (result.alreadyProcessed && Array.isArray(result.alreadyProcessed)) {
                for (const ap of result.alreadyProcessed) {
                    const existingSale = await new Promise((res) => {
                        const req = salesStore.get(ap.clientSaleId);
                        req.onsuccess = () => res(req.result);
                    });
                    if (existingSale) {
                        existingSale.synced = true;
                        existingSale.syncStatus = 'synced';
                        existingSale.billNumber = ap.billNumber;
                        existingSale.serverTransactionId = ap.transactionId;
                        existingSale.errorMessage = null;
                        salesStore.put(existingSale);
                    }
                    queueStore.delete(`OP-${ap.clientSaleId}`);
                }
            }

            // Handle rejected sales
            if (result.rejected && Array.isArray(result.rejected)) {
                for (const rej of result.rejected) {
                    const existingSale = await new Promise((res) => {
                        const req = salesStore.get(rej.clientSaleId);
                        req.onsuccess = () => res(req.result);
                    });
                    if (existingSale) {
                        existingSale.synced = false;
                        existingSale.syncStatus = 'rejected';
                        existingSale.errorMessage = rej.reason || 'Server validation rejected transaction';
                        salesStore.put(existingSale);
                    }
                    // Retain in sales store with rejection notice; remove from auto-retry queue
                    queueStore.delete(`OP-${rej.clientSaleId}`);
                }
            }

            await new Promise((resolve) => {
                tx.oncomplete = () => resolve();
            });

            // 4. Update last sync timestamp and reconcile server stock
            const nowIso = new Date().toISOString();
            localStorage.setItem('pwa_last_sync_time', nowIso);
            await this.bootstrapDealerCache();

            // Notify UI
            window.dispatchEvent(new CustomEvent('pwa-sync-completed', { detail: result }));
            this.updatePendingCount();

            return { status: 'success', result };
        } catch (err) {
            console.error('[PWA] Sync error:', err);
            return { status: 'error', error: err.message };
        } finally {
            this.isSyncing = false;
            this.updateConnectionUI();
            if (syncBtn) {
                syncBtn.disabled = !this.isOnline();
                syncBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i> Sync Now';
            }
        }
    }

    // =========================================================================
    // 7. Store Queries & Counts
    // =========================================================================

    async getPendingCount() {
        if (!this.db) return 0;
        return new Promise((resolve) => {
            const store = this.getStore('pendingQueue');
            const req = store.count();
            req.onsuccess = () => resolve(req.result || 0);
            req.onerror = () => resolve(0);
        });
    }

    async updatePendingCount() {
        const count = await this.getPendingCount();
        const badge = document.getElementById('navPendingSyncBadge');
        const offlineCountEl = document.getElementById('offlinePendingSalesCount');

        if (badge) {
            badge.innerText = count;
            if (count > 0) {
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
        }

        if (offlineCountEl) {
            offlineCountEl.innerText = count;
        }
    }

    async getAllOfflineSales() {
        return new Promise((resolve, reject) => {
            const store = this.getStore('sales');
            const req = store.getAll();
            req.onsuccess = () => {
                const sales = req.result || [];
                // Sort by timestamp descending
                sales.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                resolve(sales);
            };
            req.onerror = () => reject(req.error);
        });
    }
}

// Global PWA Singleton
window.RationSmartPWA = new RationSmartPWA();

// Global Sync helper for template buttons
function triggerPwaSync() {
    if (window.RationSmartPWA) {
        window.RationSmartPWA.syncPendingSales();
    }
}
