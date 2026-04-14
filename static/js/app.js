// ─────────────────────────────────────────────────────────────────────────
  // GLOBAL STATE VARIABLES
  // ─────────────────────────────────────────────────────────────────────────
  // These variables maintain the application state across user interactions

  const DEBUG_MODE_STORAGE_KEY = 'FabAssetsManager_debug_mode';
  const DISPLAYED_COLUMNS_STORAGE_KEY = 'FabAssetsManager_displayed_columns';
  const USER_DATA_STORAGE_KEY = 'FabAssetsManager_user_data';

  const DEFAULT_FULL_COLS_LIST = [
    'thumbnail_url',
    'uid',
    'title',
    'seller_name',
    'seller_id',
    'listing_type',
    'status',
    'asset_formats',
    'asset_format_codes',
    'tags',
    'engine_versions',
    'ue_max',
    'licenses',
    'price',
    'currency_code',
    'discounted_price',
    'media_count',
    'image_count',
    'created_at',
    'last_updated_at',
    'is_mature',
    'can_download',
    'fab_url',
  ];

  let FULL_COLS_LIST = [...DEFAULT_FULL_COLS_LIST];
  const FULL_COLUMNS_STORAGE_KEY = 'FabAssetsManager_full_columns';

  const DEFAULT_DISPLAYED_COLS_LIST = [
    'title',
    'listing_type',
    'seller_name',
    'asset_formats',
    'thumbnail_url',
    'ue_max',
    'licenses',
    'created_at',
    'can_download',
    'fab_url'
  ];

  let DISPLAYED_COLS_LIST = [...DEFAULT_DISPLAYED_COLS_LIST];
  let userAssetData = {};

  const COLUMN_LABELS = {
    thumbnail_url: 'Preview',
    uid: 'UID',
    title: 'Title',
    seller_name: 'Seller',
    seller_id: 'Seller ID',
    listing_type: 'Type',
    status: 'Status',
    asset_formats: 'Formats',
    asset_format_codes: 'Format codes',
    tags: 'Tags',
    engine_versions: 'UE Versions',
    ue_max: 'UE Max',
    licenses: 'Licenses',
    price: 'Price',
    currency_code: 'Currency',
    discounted_price: 'Discounted',
    media_count: 'Media count',
    image_count: 'Image count',
    created_at: 'Added',
    last_updated_at: 'Updated',
    is_mature: 'Mature',
    can_download: 'DL',
    fab_url: 'Fab URL',
  };

  // Asset data storage
  let allAssets = [];                    // All assets from /api/assets (full cache)
  let filteredAssets = [];               // Current filtered/sorted result set

  // Sorting state
  let sortCol = 'created_at';            // Current sort column
  let sortDir = -1;                      // Sort direction (-1: desc, 1: asc)

  // Configuration state
  let hasSavedConfig = false;            // Whether cookies/UA loaded from files

  // Pagination state
  let currentPage = 0;                   // Current page number (0-indexed)
  let itemsPerPage = 50;                 // Items per page (must match backend)

  // Selection state (for export)
  let selectedAssets = new Set();        // UIDs of selected assets (Set for dedup)

  /**
   * Purpose of each variable:
   *
   * allAssets: Complete asset list from /api/assets
   *   - Updated once on page load (loadAssets)
   *   - NOT modified by filtering (see filteredAssets)
   *   - Used for building filter options (buildFilters)
   *   - Each item includes uid, title, thumbnail_url, ue_max, licenses, etc.
   *
   * filteredAssets: Result after all filters + sort applied
   *   - Updated every time applyFilters() called
   *   - Used by renderTable() to display table rows
   *   - Pagination applied on top of this (renderTable slices)
   *   - After filtering: if 0 results, show "No results" message
   *
   * selectedAssets: UIDs of user-checked assets (for CSV/JSON export)
   *   - Uses Set<string> for O(1) lookup and automatic dedup
   *   - Updated by toggleSelectRow() and toggleSelectAll()
   *   - Sent to /api/export/csv or /api/export/json as payload
   *   - If empty and export called: exports ALL filtered assets (feature)
   *
   * Image lazy loading interacts with this state:
   * - renderTable creates <img src="/api/image/<uid>"> for each row
   * - Image download happens asynchronously (doesn't block render)
   * - Backend caches image locally after first access
   * - Modal displays cached image (no additional download)
   */


  function getSavedDebugMode() {
    return localStorage.getItem(DEBUG_MODE_STORAGE_KEY) === 'true';
  }

  function loadUserAssetData() {
    try {
      const raw = localStorage.getItem(USER_DATA_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      userAssetData = parsed && typeof parsed === 'object' ? parsed : {};
    } catch (_) {
      userAssetData = {};
    }
  }

  function saveUserAssetData() {
    localStorage.setItem(USER_DATA_STORAGE_KEY, JSON.stringify(userAssetData));
  }

  function getAssetUserData(uid) {
    if (!uid) return { favorite: false, comment: '' };
    const entry = userAssetData[uid] || {};
    return {
      favorite: Boolean(entry.favorite),
      comment: typeof entry.comment === 'string' ? entry.comment : ''
    };
  }

  function hasComment(uid) {
    return getAssetUserData(uid).comment.trim().length > 0;
  }

  function setAssetFavorite(uid, favorite) {
    if (!uid) return;
    const current = getAssetUserData(uid);
    userAssetData[uid] = {
      favorite: Boolean(favorite),
      comment: current.comment
    };
    saveUserAssetData();
  }

  function setAssetComment(uid, comment) {
    if (!uid) return;
    const current = getAssetUserData(uid);
    userAssetData[uid] = {
      favorite: current.favorite,
      comment: String(comment || '')
    };
    saveUserAssetData();
  }

  function updateDetailFavoriteUi(uid) {
    const btn = document.getElementById('detFavoriteBtn');
    if (!btn || currentDetailUid !== uid) return;

    const favorite = getAssetUserData(uid).favorite;
    btn.textContent = favorite ? '★ Favorite' : '☆ Add to favorites';
    btn.classList.toggle('is-active', favorite);
    btn.title = favorite ? 'Remove from favorites' : 'Add to favorites';
  }

  function updateDetailCommentStatus(uid) {
    const status = document.getElementById('detCommentStatus');
    if (!status || currentDetailUid !== uid) return;
    status.textContent = hasComment(uid) ? 'Comment saved locally' : 'No local comment';
  }

  function toggleFavorite(uid) {
    const current = getAssetUserData(uid);
    setAssetFavorite(uid, !current.favorite);
    renderTable(filteredAssets);
    updateDetailFavoriteUi(uid);
  }

  function toggleCurrentAssetFavorite() {
    if (!currentDetailUid) return;
    toggleFavorite(currentDetailUid);
  }

  function saveCurrentAssetComment() {
    if (!currentDetailUid) return;
    const input = document.getElementById('detLocalComment');
    if (!input) return;
    setAssetComment(currentDetailUid, input.value || '');
    renderTable(filteredAssets);
    updateDetailCommentStatus(currentDetailUid);
  }

  function clearCurrentAssetComment() {
    if (!currentDetailUid) return;
    const input = document.getElementById('detLocalComment');
    if (input) {
      input.value = '';
      input.focus();
    }
    setAssetComment(currentDetailUid, '');
    renderTable(filteredAssets);
    updateDetailCommentStatus(currentDetailUid);
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"]+/g, match => {
      switch (match) {
        case '&': return '&amp;';
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '"': return '&quot;';
        default: return match;
      }
    });
  }

  function sanitizeHtml(value) {
    const html = String(value ?? '');
    if (!html) return '';

    const template = document.createElement('template');
    template.innerHTML = html;

    template.content.querySelectorAll('script,style,iframe,object,embed,link,meta').forEach(node => node.remove());

    const allowedTags = new Set(['P', 'BR', 'UL', 'OL', 'LI', 'STRONG', 'EM', 'B', 'I', 'U', 'A', 'SPAN', 'DIV', 'TABLE', 'THEAD', 'TBODY', 'TR', 'TH', 'TD']);
    template.content.querySelectorAll('*').forEach(node => {
      if (!allowedTags.has(node.tagName)) {
        node.replaceWith(document.createTextNode(node.textContent || ''));
        return;
      }

      [...node.attributes].forEach(attr => {
        const name = attr.name.toLowerCase();
        const isSafeAnchorAttr = node.tagName === 'A' && (name === 'href' || name === 'target' || name === 'rel');
        if (!isSafeAnchorAttr) {
          node.removeAttribute(attr.name);
        }
      });

      if (node.tagName === 'A') {
        const href = node.getAttribute('href') || '';
        if (!/^https?:\/\//i.test(href)) {
          node.removeAttribute('href');
        }
        if (!node.getAttribute('target')) node.setAttribute('target', '_blank');
        if (!node.getAttribute('rel')) node.setAttribute('rel', 'noopener noreferrer');
      }
    });

    return template.innerHTML;
  }

  function hasEnrichedDetails(asset) {
    const hasDescription = !!(asset.description && asset.description.trim() && asset.description !== 'No description provided.');
    const hasGallery = Array.isArray(asset.media_urls) && asset.media_urls.length > 0;
    const hasTechSpecs = !!(asset.technical_specs && asset.technical_specs.trim());
    return hasDescription || hasGallery || hasTechSpecs;
  }

  function formatPrice(asset) {
    const price = asset.price;
    const currency = asset.currency_code || '';
    if (price === '' || price === null || price === undefined) {
      return '—';
    }
    const numeric = Number(price);
    if (Number.isFinite(numeric) && currency) {
      return `${numeric.toFixed(2)} ${currency}`;
    }
    return currency ? `${price} ${currency}` : String(price);
  }

  function setFilterByClick(filterClass, value) {
    document.querySelectorAll('.' + filterClass).forEach(cb => {
      if (cb.value === value) cb.checked = true;
    });
    // Open the corresponding details tag if it's closed
    const cb = document.querySelector('.' + filterClass);
    if (cb) {
      const details = cb.closest('details');
      if (details) details.open = true;
    }

    // Close modal if open
    const detModal = document.getElementById('assetDetailsModal');
    if (detModal && detModal.style.display !== 'none') {
      detModal.style.display = 'none';
    }

    applyFilters();
  }

  function renderTagList(value, filterClass) {
    const items = String(value || '')
      .split(',')
      .map(item => item.trim())
      .filter(Boolean);
    if (!items.length) {
      return '<span style="color:var(--text2)">—</span>';
    }
    if (filterClass) {
      return items.map(item => `<span class="tag" style="cursor:pointer;" onclick="setFilterByClick('${filterClass}', '${escapeHtml(item)}')">${escapeHtml(item)}</span>`).join(' ');
    }
    return items.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join(' ');
  }

  function renderColumnValue(asset, column) {
    const uid = asset.uid || '';
    const meta = getAssetUserData(uid);
    const favoriteBtn = `<button class="favorite-toggle ${meta.favorite ? 'is-favorite' : ''}" type="button" onclick="toggleFavorite('${uid}')" title="${meta.favorite ? 'Remove favorite' : 'Add favorite'}">${meta.favorite ? '★' : '☆'}</button>`;
    const commentBadge = meta.comment.trim()
      ? '<span class="local-comment-indicator" title="Local comment saved">📝</span>'
      : '';

    switch (column) {
      case 'thumbnail_url':
        return asset.thumbnail_url
          ? `<img class="preview-thumb" src="/api/image/${asset.uid || ''}" alt="Preview" onerror="this.style.display='none'" onclick="showImageModal('${asset.uid}')" style="cursor:pointer; max-width:60px; max-height:40px; border-radius:4px; object-fit:cover;">`
          : '<span style="color:var(--text2)">—</span>';
      case 'title':
        return `<div class="title-cell-wrap">${favoriteBtn}<a href="javascript:void(0)" onclick="showAssetDetailsModal('${asset.uid}')" title="${escapeHtml(asset.title || '')}">${escapeHtml(asset.title || '—')}</a>${commentBadge}</div>`;
      case 'seller_name':
        return asset.seller_name ? `<a href="javascript:void(0)" style="color:inherit;text-decoration:underline dashed;" onclick="setFilterByClick('seller-cb', '${escapeHtml(asset.seller_name)}')">${escapeHtml(asset.seller_name)}</a>` : '—';
      case 'listing_type':
        return asset.listing_type ? `<a href="javascript:void(0)" style="color:inherit;text-decoration:underline dashed;" onclick="setFilterByClick('type-cb', '${escapeHtml(asset.listing_type)}')">${escapeHtml(asset.listing_type)}</a>` : '—';
      case 'created_at':
      case 'last_updated_at':
        return asset[column] ? escapeHtml(asset[column].substring(0, 10)) : '—';
      case 'can_download':
        return asset.can_download
          ? '<span class="icon-check" title="Downloadable">✓</span>'
          : '<span class="icon-cross">—</span>';
      case 'is_mature':
        return asset.is_mature ? 'Yes' : 'No';
      case 'price':
        return escapeHtml(formatPrice(asset));
      case 'licenses':
        return renderTagList(asset[column], 'license-cb');
      case 'engine_versions':
        return renderTagList(asset[column], 'engine-cb');
      case 'asset_formats':
        return renderTagList(asset[column], 'format-cb');
      case 'asset_format_codes':
      case 'tags':
        return renderTagList(asset[column], null);
      case 'fab_url':
        return asset.fab_url ? `<a class="btn btn-ghost btn-sm" href="${escapeHtml(asset.fab_url)}" target="_blank">Open</a>` : '—';
      default:
        return escapeHtml(asset[column] ?? '—');
    }
  }

  function getColumnClass(column) {
    if (column === 'title') return 'asset-title';
    if (column === 'created_at' || column === 'last_updated_at') return 'date-cell';
    return '';
  }

  function getColumnStyle(column) {
    if (column === 'thumbnail_url') return 'style="width:80px;text-align:center;padding:4px"';
    if (column === 'uid') return 'style="font-family:monospace;font-size:0.78rem;white-space:nowrap"';
    if (column === 'can_download' || column === 'is_mature') return 'style="text-align:center;white-space:nowrap"';
    if (column === 'price') return 'style="white-space:nowrap"';
    return '';
  }

  function getColumnHeader(column) {
    return COLUMN_LABELS[column] || column;
  }

  function isSortableColumn(column) {
    return ['title', 'created_at', 'last_updated_at', 'seller_name', 'listing_type', 'asset_formats'].includes(column);
  }

  function getColumnSortHandler(column) {
    return `sortBy('${column}')`;
  }

  function saveDebugMode(value) {
    localStorage.setItem(DEBUG_MODE_STORAGE_KEY, value ? 'true' : 'false');
  }

  function getSavedLogSettings() {
    try {
      const raw = localStorage.getItem('FabAssetsManager_log_settings');
      return raw ? JSON.parse(raw) : {};
    } catch (_) {
      return {};
    }
  }

  function saveLogSettings(level, output, debugMode) {
    localStorage.setItem('FabAssetsManager_log_settings', JSON.stringify({ level, output, debugMode: !!debugMode }));
  }

  function loadFullColumnsList() {
    try {
      const raw = localStorage.getItem(FULL_COLUMNS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        const valid = parsed.filter(col => DEFAULT_FULL_COLS_LIST.includes(col));
        const missing = DEFAULT_FULL_COLS_LIST.filter(col => !valid.includes(col));
        FULL_COLS_LIST = [...valid, ...missing];
      }
    } catch (_) {
      FULL_COLS_LIST = [...DEFAULT_FULL_COLS_LIST];
    }
  }

  function saveFullColumnsList() {
    localStorage.setItem(FULL_COLUMNS_STORAGE_KEY, JSON.stringify(FULL_COLS_LIST));
  }

  function loadDisplayedColumns() {
    try {
      const raw = localStorage.getItem(DISPLAYED_COLUMNS_STORAGE_KEY);
      if (!raw) {
        DISPLAYED_COLS_LIST = [...DEFAULT_DISPLAYED_COLS_LIST];
        return;
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        DISPLAYED_COLS_LIST = [...DEFAULT_DISPLAYED_COLS_LIST];
        return;
      }
      const valid = parsed.filter(col => FULL_COLS_LIST.includes(col));

      // Order them by FULL_COLS_LIST order
      DISPLAYED_COLS_LIST = FULL_COLS_LIST.filter(c => valid.includes(c));

      if (!DISPLAYED_COLS_LIST.length) {
        DISPLAYED_COLS_LIST = [...DEFAULT_DISPLAYED_COLS_LIST];
      }
    } catch (_) {
      DISPLAYED_COLS_LIST = [...DEFAULT_DISPLAYED_COLS_LIST];
    }
  }

  function saveDisplayedColumns() {
    localStorage.setItem(DISPLAYED_COLUMNS_STORAGE_KEY, JSON.stringify(DISPLAYED_COLS_LIST));
  }

  let draggedCol = null;

  function dragColStart(event, col) {
    draggedCol = col;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', col);
    event.target.style.opacity = '0.5';
  }

  function dragColOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }

  function dragColEnd(event) {
    event.target.style.opacity = '1';
  }

  function dropCol(event, targetCol) {
    event.preventDefault();
    if (!draggedCol || draggedCol === targetCol) return;

    const fromIdx = FULL_COLS_LIST.indexOf(draggedCol);
    const toIdx = FULL_COLS_LIST.indexOf(targetCol);
    if (fromIdx < 0 || toIdx < 0) return;

    FULL_COLS_LIST.splice(fromIdx, 1);
    FULL_COLS_LIST.splice(toIdx, 0, draggedCol);

    // Update DISPLAYED_COLS_LIST order
    DISPLAYED_COLS_LIST = FULL_COLS_LIST.filter(c => DISPLAYED_COLS_LIST.includes(c));

    saveFullColumnsList();
    saveDisplayedColumns();
    renderColumnsSelector();
    renderTable(filteredAssets);
  }

  function renderColumnsSelector() {
    const container = document.getElementById('columnsFilter');
    if (!container) return;

    container.innerHTML = FULL_COLS_LIST.map(col => {
      const checked = DISPLAYED_COLS_LIST.includes(col) ? 'checked' : '';
      const disabled = (col === 'title' || col === 'seller_name') ? 'disabled' : '';
      const label = escapeHtml(getColumnHeader(col));
      return `
        <label class="filter-label" draggable="true" ondragstart="dragColStart(event, '${col}')" ondragend="dragColEnd(event)" ondragover="dragColOver(event)" ondrop="dropCol(event, '${col}')" style="cursor: grab; ${disabled ? 'opacity:0.6;' : ''}">
          <span style="margin-right: 4px; color: var(--text2); user-select: none;">☰</span>
          <input type="checkbox" class="column-cb" value="${col}" ${checked} ${disabled} onchange="toggleColumn(this)" />
          ${label}
        </label>`;
    }).join('');
  }

  function toggleColumn(checkbox) {
    const col = checkbox.value;
    if (col === 'title' || col === 'seller_name') {
      checkbox.checked = true;
      return;
    }
    if (checkbox.checked) {
      if (!DISPLAYED_COLS_LIST.includes(col)) {
        DISPLAYED_COLS_LIST.push(col);
      }
    } else {
      const next = DISPLAYED_COLS_LIST.filter(c => c !== col);
      if (!next.length) {
        checkbox.checked = true;
        return;
      }
      DISPLAYED_COLS_LIST = next;
    }
    saveDisplayedColumns();
    renderColumnsSelector();
    renderTable(filteredAssets);
  }

  function selectAllColumns() {
    DISPLAYED_COLS_LIST = [...FULL_COLS_LIST];
    saveDisplayedColumns();
    renderColumnsSelector();
    renderTable(filteredAssets);
  }

  function resetColumnsToDefault() {
    FULL_COLS_LIST = [...DEFAULT_FULL_COLS_LIST];
    DISPLAYED_COLS_LIST = [...DEFAULT_DISPLAYED_COLS_LIST];
    saveFullColumnsList();
    saveDisplayedColumns();
    renderColumnsSelector();
    renderTable(filteredAssets);
  }

  // ─── Init ─────────────────────────────────────────────────
  async function init() {
    loadFullColumnsList();
    loadDisplayedColumns();
    loadUserAssetData();
    renderColumnsSelector();

    const debugCheckbox = document.getElementById('debugMode');
    if (debugCheckbox) {
      debugCheckbox.checked = getSavedDebugMode();
    }

    await loadSavedConfig();
    await refreshCacheInfo();

    const resp = await fetch('/api/status');
    const status = await resp.json();
    if (status.cached > 0) {
      await loadAssets();
      return;
    }

    if (hasSavedConfig) {
      await fetchAssets({ useSavedConfig: true, openModalOnMissingConfig: false });
    }
  }

  async function loadSavedConfig() {
    try {
      const resp = await fetch('/api/config');
      const config = await resp.json();
      hasSavedConfig = Boolean(config.has_cookies && config.has_user_agent);
      if (config.user_agent) {
        document.getElementById('uaInput').value = config.user_agent;
      }
      if (config.log_level) {
        document.getElementById('logLevelSelect').value = config.log_level;
      }
      if (config.log_output) {
        document.getElementById('logOutputSelect').value = config.log_output;
      }

      const debugCheckbox = document.getElementById('debugMode');
      if (typeof config.debug_mode === 'boolean') {
        debugCheckbox.checked = config.debug_mode;
      } else {
        const saved = getSavedLogSettings();
        if (saved.level) document.getElementById('logLevelSelect').value = saved.level;
        if (saved.output) document.getElementById('logOutputSelect').value = saved.output;
        if (typeof saved.debugMode === 'boolean') debugCheckbox.checked = saved.debugMode;
      }
    } catch (_) {
      hasSavedConfig = false;
    }
  }

  async function handleLoadLibraryClick() {
    // Always try first with saved config
    // If it fails because it doesn't exist, the modal will open
    await fetchAssets({ useSavedConfig: true, openModalOnMissingConfig: true });
  }

  /**
   * Load cached assets from backend and render table.
   *
   * Assets are fetched via GET /api/assets which returns flattened format:
   * [
   *   { uid, title, ue_max, licenses, created_at, last_updated_at,
   *     can_download, fab_url, thumbnail_url },
   *   ...
   * ]
   *
   * The thumbnail_url field enables lazy loading in renderTable():
   * - Preview images show as <img src="/api/image/<uid>">
   * - Backend /api/image/<uid> checks cache, downloads if needed, returns JPEG
   * - Images never block initial page load (loaded by browser as needed)
   *
   * Flow:
   * 1. Show progress bar (20%)
   * 2. GET /api/assets → returns all cached assets
   * 3. Parse JSON (70%)
   * 4. Build filter options (100%)
   * 5. Apply filters (initial render)
   * 6. Hide progress bar
   *
   * @async
   */
  async function loadAssets() {
    setProgress(20);
    const resp = await fetch('/api/assets');
    setProgress(70);
    allAssets = await resp.json();
    setProgress(100);
    buildFilters();
    applyFilters();
    await refreshCacheInfo();
    setTimeout(() => setProgress(0), 500);
  }

  async function refreshCacheInfo() {
    const badge = document.getElementById('cacheBadge');
    if (!badge) return;

    try {
      const resp = await fetch('/api/cache-info');
      const data = await resp.json();
      if (!resp.ok || !data.has_cache) {
        badge.textContent = 'Last synced: —';
        badge.title = 'No cached assets yet';
        return;
      }

      const label = data.last_sync_label || data.timestamp || '—';
      badge.textContent = `Last synced: ${label}`;
      badge.title = data.last_sync_at ? `Cache updated at ${data.last_sync_at}` : 'Cache updated recently';
    } catch (err) {
      badge.textContent = 'Last synced: —';
      badge.title = 'Cache information unavailable';
    }
  }

  // ─── Fetch via cookies ────────────────────────────────────
  function openCookieModal() {
    document.getElementById('cookieModal').classList.add('open');
    document.getElementById('modalError').style.display = 'none';
  }
  function closeCookieModal() {
    document.getElementById('cookieModal').classList.remove('open');
  }

  async function fetchAssets(opts) {
    opts = opts || {};
    let cookies = '', userAgent = '';

    if (opts.useSavedConfig) {
      cookies = '';
      userAgent = '';
      console.log('🔄 Using saved config (config/cookies.txt + config/user_agent.txt)');
    } else {
      cookies = document.getElementById('cookieInput').value.trim();
      userAgent = document.getElementById('uaInput').value.trim();
    }

    const debugMode = document.getElementById('debugMode').checked;
    saveDebugMode(debugMode);

    if (!opts.useSavedConfig && !cookies && opts.openModalOnMissingConfig !== false) {
      openCookieModal();
      return;
    }

    const btn = document.getElementById('fetchBtn');
    const err = document.getElementById('modalError');

    // Show loading in header when no modal is shown
    const totalBadge = document.getElementById('totalBadge');
    const oldBadgeText = totalBadge.textContent;
    if (opts.useSavedConfig) {
      totalBadge.textContent = 'Loading...';
      totalBadge.classList.add('accent');
    }

    if (btn) btn.disabled = true;
    if (btn) btn.innerHTML = '<span class="spinner"></span> Loading...';
    if (err) err.style.display = 'none';
    setProgress(10);

    try {
      const resp = await fetch('/api/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookies, user_agent: userAgent, debug: debugMode }),
      });
      setProgress(80);
      const data = await resp.json();
      if (!resp.ok) {
        const errMsg = data.error || 'Unknown error';
        console.error('❌ Fetch error:', errMsg);

        // Restaurer le badge
        if (opts.useSavedConfig) {
          totalBadge.textContent = oldBadgeText;
          totalBadge.classList.remove('accent');
        }

        if (err) {
          err.textContent = errMsg;
          err.style.display = 'block';
        }
        if (opts.openModalOnMissingConfig) {
          openCookieModal();
        }

        // Show an alert when no modal is shown
        if (opts.useSavedConfig) {
          alert('❌ Error: ' + errMsg + '\n\nCheck the console (F12) for more details.');
        }
        setProgress(0);
        return;
      }

      console.log('✅ Assets loaded:', data.count);
      closeCookieModal();
      await loadAssets();
      await loadSavedConfig();

      // Restaurer le badge avec le nouveau total
      if (opts.useSavedConfig) {
        totalBadge.classList.remove('accent');
      }
    } catch(e) {
      const errMsg = 'Network error: ' + e.message;
      console.error('❌', errMsg);

      // Restaurer le badge
      if (opts.useSavedConfig) {
        totalBadge.textContent = oldBadgeText;
        totalBadge.classList.remove('accent');
      }

      if (err) {
        err.textContent = errMsg;
        err.style.display = 'block';
      }

      // Show an alert when no modal is shown
      if (opts.useSavedConfig) {
        alert('❌ Network error: ' + e.message);
      }
      setProgress(0);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '🚀 Load';
      }
    }
  }

  // ─── Filters ──────────────────────────────────────────────
  // ─── Batch Details (CI11) ──────────────────────────────────
  let _batchAbortController = null;

  function getSelectedUids() {
    return Array.from(selectedAssets);
  }

  async function startBatchDetails() {
    // Determine which UIDs to fetch details for
    let targetUids = getSelectedUids();

    // CI12: If no specific assets selected, default to all CURRENTLY FILTERED assets
    if (targetUids.length === 0) {
      if (filteredAssets && filteredAssets.length > 0) {
        targetUids = filteredAssets.map(a => a.uid || (a.listing && a.listing.uid));
        // Ensure no undefined
        targetUids = targetUids.filter(uid => uid);
      }
    }

    let missingUids = [];

    const btnGetDetails = document.getElementById('btnGetDetails');
    const btnStopScrap = document.getElementById('btnStopScrap');

    try {
      // Build fetch options using POST to avoid URL length limits with many UIDs
      const url = '/api/missing_details';
      const fetchOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ uids: targetUids })
      };

      const resp = await fetch(url, fetchOptions);
      missingUids = await resp.json();

      if (!missingUids.length) {
        alert(targetUids.length > 0
          ? "Selected/Filtered assets already have full details!"
          : "All assets already possess full details!");
        return;
      }

      const scopeMsg = targetUids.length > 0
        ? `${missingUids.length} missing among the ${targetUids.length} queried asset(s)`
        : `${missingUids.length} assets`;

      if (!confirm(`Found ${scopeMsg} missing details.\nFetch them now?`)) return;

    } catch(e) {
      alert("Error checking missing details: " + e.message);
      return;
    }

    // Setup abort controller for stop functionality
    _batchAbortController = new AbortController();
    const signal = _batchAbortController.signal;

    // Show stop button, hide get details button
    btnGetDetails.style.display = 'none';
    btnStopScrap.style.display = 'inline-flex';

    const totalBadge = document.getElementById('totalBadge');
    const oldBadgeText = totalBadge.textContent;
    let stopped = false;

    for (let i = 0; i < missingUids.length; i++) {
      if (signal.aborted) { stopped = true; break; }

      const uid = missingUids[i];
      totalBadge.textContent = `Enriching ${i + 1}/${missingUids.length}...`;
      totalBadge.classList.add('accent');
      setProgress(((i + 1) / missingUids.length) * 100);

      try {
        await fetch(`/api/details/${uid}`, { signal });
      } catch(err) {
        if (err.name === 'AbortError') { stopped = true; break; }
        console.error("Error fetching detail for", uid, err);
      }
    }

    totalBadge.textContent = oldBadgeText;
    totalBadge.classList.remove('accent');
    setProgress(0);

    // Restore buttons
    btnGetDetails.style.display = 'inline-flex';
    btnStopScrap.style.display = 'none';
    _batchAbortController = null;

    if (stopped) {
      console.log('⏹ Scraping stopped by user');
    } else {
      alert("Batch processing complete.");
    }

    await loadAssets();
  }

  function stopBatchDetails() {
    if (_batchAbortController) {
      _batchAbortController.abort();
    }
  }

  function filterSellers() {
    const searchVal = document.getElementById('sellerSearch').value.toLowerCase();
    const sellerLabels = document.querySelectorAll('#sellerFilter .filter-label');
    sellerLabels.forEach(label => {
      const input = label.querySelector('input');
      if (input) {
        const sellerName = input.value.toLowerCase();
        if (sellerName.includes(searchVal)) {
          label.style.display = '';
        } else {
          label.style.display = 'none';
        }
      }
    });
  }

  function buildFilters() {
    // Engine versions
    const engines = {};
    const licenses = {};
    const sellers = {};
    const formats = {};
    const types = {};
    const ueMaxVersions = {};

    allAssets.forEach(a => {
      (a.engine_versions || '').split(',').map(s => s.trim()).filter(Boolean).forEach(v => {
        engines[v] = (engines[v] || 0) + 1;
      });
      (a.licenses || '').split(',').map(s => s.trim()).filter(Boolean).forEach(l => {
        licenses[l] = (licenses[l] || 0) + 1;
      });
      (a.asset_formats || '').split(',').map(s => s.trim()).filter(Boolean).forEach(f => {
        formats[f] = (formats[f] || 0) + 1;
      });
      if (a.seller_name) {
        sellers[a.seller_name] = (sellers[a.seller_name] || 0) + 1;
      }
      if (a.listing_type) {
        types[a.listing_type] = (types[a.listing_type] || 0) + 1;
      }
      if (a.ue_max) {
        ueMaxVersions[a.ue_max] = (ueMaxVersions[a.ue_max] || 0) + 1;
      }
    });

    const engineDiv = document.getElementById('engineFilter');
    engineDiv.innerHTML = Object.entries(engines)
      .sort((a,b) => b[0].localeCompare(a[0]))
      .map(([v, c]) => `
        <label class="filter-label">
          <input type="checkbox" class="engine-cb" value="${escapeHtml(v)}" onchange="applyFilters()" />
          ${escapeHtml(v)} <span class="filter-count">${c}</span>
        </label>`).join('');

    const licDiv = document.getElementById('licenseFilter');
    licDiv.innerHTML = Object.entries(licenses)
      .sort((a,b) => b[1] - a[1])
      .map(([l, c]) => `
        <label class="filter-label">
          <input type="checkbox" class="license-cb" value="${escapeHtml(l)}" onchange="applyFilters()" />
          ${escapeHtml(l)} <span class="filter-count">${c}</span>
        </label>`).join('');

    const formatDiv = document.getElementById('formatFilter');
    formatDiv.innerHTML = Object.entries(formats)
      .sort((a,b) => b[1] - a[1])
      .map(([f, c]) => `
        <label class="filter-label">
          <input type="checkbox" class="format-cb" value="${escapeHtml(f)}" onchange="applyFilters()" />
          ${escapeHtml(f)} <span class="filter-count">${c}</span>
        </label>`).join('');

    const sellerDiv = document.getElementById('sellerFilter');
    sellerDiv.innerHTML = Object.entries(sellers)
      .sort((a,b) => a[0].localeCompare(b[0]))
      .map(([s, c]) => `
        <label class="filter-label">
          <input type="checkbox" class="seller-cb" value="${escapeHtml(s)}" onchange="applyFilters()" />
          ${escapeHtml(s)} <span class="filter-count">${c}</span>
        </label>`).join('');

    const typeDiv = document.getElementById('typeFilter');
    typeDiv.innerHTML = Object.entries(types)
      .sort((a,b) => b[1] - a[1])
      .map(([t, c]) => `
        <label class="filter-label">
          <input type="checkbox" class="type-cb" value="${escapeHtml(t)}" onchange="applyFilters()" />
          ${escapeHtml(t)} <span class="filter-count">${c}</span>
        </label>`).join('');

    const ueMaxDiv = document.getElementById('ueMaxFilter');
    const sortedVersions = Object.keys(ueMaxVersions).sort((a, b) => {
      const aParts = a.split('.').map(Number);
      const bParts = b.split('.').map(Number);
      for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
        const aN = aParts[i] || 0;
        const bN = bParts[i] || 0;
        if (aN !== bN) return aN - bN;
      }
      return 0;
    });
    ueMaxDiv.innerHTML = sortedVersions
      .map(v => `
        <label class="filter-label">
          <input type="checkbox" class="ue-max-cb" value="${escapeHtml(v)}" onchange="applyFilters()" />
          ${escapeHtml(v)} <span class="filter-count">${ueMaxVersions[v]}</span>
        </label>`).join('');

    // Restore saved filters (CI5)
    restoreFiltersState();
  }

  const FILTERS_STORAGE_KEY = 'FabAssetsManager_filters_state';

  function saveFiltersState() {
    const state = {
      q: document.getElementById('searchInput').value,
      sort: document.getElementById('sortSelect').value,
      engines: [...document.querySelectorAll('.engine-cb:checked')].map(c => c.value),
      licenses: [...document.querySelectorAll('.license-cb:checked')].map(c => c.value),
      formats: [...document.querySelectorAll('.format-cb:checked')].map(c => c.value),
      sellers: [...document.querySelectorAll('.seller-cb:checked')].map(c => c.value),
      types: [...document.querySelectorAll('.type-cb:checked')].map(c => c.value),
      ueMax: [...document.querySelectorAll('.ue-max-cb:checked')].map(c => c.value),
      onlyDownloadable: document.getElementById('filterDownloadable').checked,
      onlyDiscounted: document.getElementById('filterDiscounted').checked,
      hideMature: document.getElementById('filterMature').checked,
      favoritesOnly: document.getElementById('filterFavoritesOnly').checked,
      withLocalNote: document.getElementById('filterWithLocalNote').checked
    };
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(state));
  }

  function restoreFiltersState() {
    try {
      const raw = localStorage.getItem(FILTERS_STORAGE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw);

      if (state.q) document.getElementById('searchInput').value = state.q;
      if (state.sort) document.getElementById('sortSelect').value = state.sort;

      const setChecks = (selector, values) => {
        if (!values || !values.length) return;
        document.querySelectorAll(selector).forEach(cb => {
          if (values.includes(cb.value)) cb.checked = true;
        });
      };

      setChecks('.engine-cb', state.engines);
      setChecks('.license-cb', state.licenses);
      setChecks('.format-cb', state.formats);
      setChecks('.seller-cb', state.sellers);
      setChecks('.type-cb', state.types);
      setChecks('.ue-max-cb', state.ueMax);

      if (state.onlyDownloadable !== undefined) document.getElementById('filterDownloadable').checked = state.onlyDownloadable;
      if (state.onlyDiscounted !== undefined) document.getElementById('filterDiscounted').checked = state.onlyDiscounted;
      if (state.hideMature !== undefined) document.getElementById('filterMature').checked = state.hideMature;
      if (state.favoritesOnly !== undefined) document.getElementById('filterFavoritesOnly').checked = state.favoritesOnly;
      if (state.withLocalNote !== undefined) document.getElementById('filterWithLocalNote').checked = state.withLocalNote;
    } catch(e) {
      console.warn("Could not restore filters state", e);
    }
  }

  function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('sortSelect').value = 'date_desc';
    document.querySelectorAll('.filter-group input[type="checkbox"]').forEach(cb => cb.checked = false);
    // don't uncheck debug mode since it's in options but not a content filter
    document.getElementById('debugMode').checked = getSavedDebugMode();
    saveFiltersState();
    applyFilters();
  }

  /* ─── Maintenance Actions ──────────────────────────────────────────────────────── */

  async function clearPreviews() {
    if (!confirm("Are you sure you want to delete all downloaded preview images? This will free up disk space.")) {
      return;
    }
    try {
      const res = await fetch('/api/clear_previews', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || "Error clearing previews");
      alert(data.message);
    } catch (err) {
      console.error(err);
      alert("Failed to clear previews: " + err.message);
    }
  }

  async function clearCache() {
    if (!confirm("WARNING: Are you sure you want to clear the entire local cache? All asset data will be deleted and you will need to fetch it again.")) {
      return;
    }
    try {
      const res = await fetch('/api/clear_cache', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || "Error clearing cache");
      alert(data.message);
      // Reload assets after cache is cleared
      loadAssets();
      updateCacheInfo();
    } catch (err) {
      console.error(err);
      alert("Failed to clear cache: " + err.message);
    }
  }

  /**
   * Apply all active filters and re-render table.
   *
   * Filters applied:
   * 1. TEXT SEARCH (q) - Case-insensitive title search
  * 2. UE VERSIONS - Filter by supported UE versions (multi-select)
   * 3. UE MAX - Filter by max supported version (multi-select, semantic sort)
   * 4. LICENSES - Filter by license type (multi-select)
   * 5. DOWNLOADABLE - Only show assets that can be downloaded
   * 6. MATURE - Hide mature/adult content
   *
   * Sorting options:
   * - title_asc: Title A→Z (alphabetical ascending)
   * - title_desc: Title Z→A (alphabetical descending)
   * - date_asc: Oldest first (creation date)
   * - date_desc: Newest first (creation date)
   * - updated_desc: Most recently updated first
   *
   * Each asset includes these filterable fields:
   * - title: Asset display name (for text search)
   * - engine_versions: Comma-separated list of all supported UE versions
   * - ue_max: Maximum supported version (for UE Max filter)
   * - licenses: Comma-separated license names
   * - can_download: Boolean - whether downloadable
   * - is_mature: Boolean - whether adult content
   *
   * After filtering and sorting:
   * - Updates result badges (total / displayed counts)
   * - Resets pagination to page 0
   * - Calls renderTable() to update displayed rows
   * - Image lazy loading happens during renderTable (src="/api/image/<uid>")
   */
  function applyFilters() {
    saveFiltersState();
    currentPage = 0; // Reset to first page when filters change
    const q = document.getElementById('searchInput').value.toLowerCase();
    const selectedEngines = [...document.querySelectorAll('.engine-cb:checked')].map(c => c.value);
    const selectedLicenses = [...document.querySelectorAll('.license-cb:checked')].map(c => c.value);
    const selectedFormats = [...document.querySelectorAll('.format-cb:checked')].map(c => c.value);
    const selectedSellers = [...document.querySelectorAll('.seller-cb:checked')].map(c => c.value);
    const selectedTypes = [...document.querySelectorAll('.type-cb:checked')].map(c => c.value);
    const selectedUeMax = [...document.querySelectorAll('.ue-max-cb:checked')].map(c => c.value);
    const onlyDownloadable = document.getElementById('filterDownloadable').checked;
    const onlyDiscounted = document.getElementById('filterDiscounted').checked;
    const hideMature = document.getElementById('filterMature').checked;
    const favoritesOnly = document.getElementById('filterFavoritesOnly').checked;
    const withLocalNote = document.getElementById('filterWithLocalNote').checked;
    const sort = document.getElementById('sortSelect').value;

    let result = allAssets.filter(a => {
      if (q && !a.title.toLowerCase().includes(q)) return false;
      if (selectedEngines.length) {
        const ev = (a.engine_versions || '').split(',').map(s => s.trim());
        if (!selectedEngines.some(e => ev.includes(e))) return false;
      }
      if (selectedLicenses.length) {
        const lics = (a.licenses || '').split(',').map(s => s.trim());
        if (!selectedLicenses.some(l => lics.includes(l))) return false;
      }
      if (selectedFormats.length) {
        const fmts = (a.asset_formats || '').split(',').map(s => s.trim());
        if (!selectedFormats.some(f => fmts.includes(f))) return false;
      }
      if (selectedSellers.length) {
        if (!selectedSellers.includes(a.seller_name || '')) return false;
      }
      if (selectedTypes.length) {
        if (!selectedTypes.includes(a.listing_type || '')) return false;
      }
      if (selectedUeMax.length) {
        if (!selectedUeMax.includes(a.ue_max || '')) return false;
      }
      if (onlyDownloadable && !a.can_download) return false;
      if (onlyDiscounted && (!a.discounted_price || a.discounted_price === a.price)) return false;
      if (hideMature && a.is_mature) return false;
      if (favoritesOnly && !getAssetUserData(a.uid || '').favorite) return false;
      if (withLocalNote && !hasComment(a.uid || '')) return false;
      return true;
    });

    // Sort
    result.sort((a, b) => {
      const aVal = a.title || '';
      const bVal = b.title || '';
      const cmp = aVal.localeCompare(bVal);
      switch (sort) {
        case 'title_asc': return cmp;
        case 'title_desc': return -cmp;
        case 'seller_asc': return (a.seller_name || '').localeCompare(b.seller_name || '');
        case 'seller_desc': return (b.seller_name || '').localeCompare(a.seller_name || '');
        case 'type_asc': return (a.listing_type || '').localeCompare(b.listing_type || '');
        case 'type_desc': return (b.listing_type || '').localeCompare(a.listing_type || '');
        case 'format_asc': return (a.asset_formats || '').localeCompare(b.asset_formats || '');
        case 'format_desc': return (b.asset_formats || '').localeCompare(a.asset_formats || '');
        case 'date_asc': return (a.created_at || '').localeCompare(b.created_at || '');
        case 'date_desc': return (b.created_at || '').localeCompare(a.created_at || '');
        case 'updated_desc': return (b.last_updated_at || '').localeCompare(a.last_updated_at || '');
        default: return 0;
      }
    });

    if (sort.startsWith('title_')) sortCol = 'title';
    else if (sort.startsWith('seller_')) sortCol = 'seller_name';
    else if (sort.startsWith('type_')) sortCol = 'listing_type';
    else if (sort.startsWith('format_')) sortCol = 'asset_formats';
    else if (sort.startsWith('date_')) sortCol = 'created_at';
    else if (sort.startsWith('updated_')) sortCol = 'last_updated_at';

    filteredAssets = result;
    renderTable(result);

    const total = allAssets.length;
    document.getElementById('totalBadge').textContent = `${total} assets`;
    const filtBadge = document.getElementById('filteredBadge');
    if (result.length < total) {
      filtBadge.textContent = `${result.length} shown`;
      filtBadge.style.display = '';
    } else {
      filtBadge.style.display = 'none';
    }
    document.getElementById('resultsInfo').textContent =
      `${result.length} asset${result.length > 1 ? 's' : ''} shown out of ${total}`;
  }

  /**
   * Render paginated asset table with dynamic columns.
   *
   * The visible columns are driven by DISPLAYED_COLS_LIST.
   */
  function renderTable(assets) {
    const wrapper = document.getElementById('tableWrapper');

    if (!assets.length && allAssets.length === 0) {
      wrapper.innerHTML = `
        <div class="empty-state">
          <div class="icon">📦</div>
          <h2>No assets loaded</h2>
          <p>Click <strong>🔄 Get New Assets</strong> to try automatic loading, or enter your cookies.</p>
          <button class="btn btn-primary" onclick="handleLoadLibraryClick()">Load My Library</button>
        </div>`;
      return;
    }

    if (!assets.length) {
      wrapper.innerHTML = `
        <div class="empty-state">
          <div class="icon">🔍</div>
          <h2>No results</h2>
          <p>No assets match your filters.</p>
          <button class="btn btn-ghost" onclick="clearFilters()">Reset</button>
        </div>`;
      return;
    }

    const pageCount = Math.ceil(assets.length / itemsPerPage);
    const start = currentPage * itemsPerPage;
    const end = Math.min(start + itemsPerPage, assets.length);
    const pageAssets = assets.slice(start, end);

    const rows = pageAssets.map(a => {
      const uid = a.uid || '';
      const isSelected = selectedAssets.has(uid);
      const checkboxClass = isSelected ? 'checked' : '';
      const dynamicCells = DISPLAYED_COLS_LIST.map(column => {
        const cls = getColumnClass(column);
        const style = getColumnStyle(column);
        return `<td${cls ? ` class="${cls}"` : ''}${style ? ` ${style}` : ''}>${renderColumnValue(a, column)}</td>`;
      }).join('');

      return `<tr class="${checkboxClass}">
        <td class="checkbox-col" style="width:40px;text-align:center;padding:0 8px">
          <input type="checkbox" class="row-checkbox" data-uid="${uid}" onchange="toggleSelectRow(this)" ${isSelected ? 'checked' : ''} />
        </td>
        ${dynamicCells}
      </tr>`;
    }).join('');

    const allOnPageSelected = pageAssets.length > 0 && pageAssets.every(a => selectedAssets.has(a.uid || ''));
    const dynamicHeaders = DISPLAYED_COLS_LIST.map(column => {
      const label = escapeHtml(getColumnHeader(column));
      const sortHandler = isSortableColumn(column) ? ` onclick="${getColumnSortHandler(column)}"` : '';
      const sortedClass = sortCol === column ? ' sorted' : '';
      const sortIcon = isSortableColumn(column) ? ' <span class="sort-icon">⇅</span>' : '';
      return `<th class="${sortedClass}"${sortHandler}>${label}${sortIcon}</th>`;
    }).join('');

    const tableHTML = `
      <table>
        <thead>
          <tr>
            <th class="checkbox-col" style="width:40px;text-align:center;padding:0 8px">
              <input type="checkbox" id="selectAllCheckbox" onchange="toggleSelectAll(this)" ${allOnPageSelected && pageAssets.length > 0 ? 'checked' : ''} title="Select all assets on this page" />
            </th>
            ${dynamicHeaders}
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;

    let paginationHTML = '';
    if (pageCount > 1 || assets.length > 20) {
      let pageSelectOptions = '';
      for (let i = 0; i < pageCount; i++) {
        const isSelected = i === currentPage ? 'selected' : '';
        pageSelectOptions += `<option value="${i}" ${isSelected}>Page ${i + 1} / ${pageCount}</option>`;
      }

      const itemsPerPageOptions = [20, 50, 100].map(val =>
        `<option value="${val}" ${itemsPerPage === val ? 'selected' : ''}>${val} per page</option>`
      ).join('');

      paginationHTML = `
        <div class="pagination-controls" style="margin-top:16px;display:flex;gap:12px;justify-content:center;align-items:center;flex-wrap:wrap">
          <div style="display:flex;gap:6px;align-items:center;">
            <button class="pagination-btn" onclick="goToPage(0)" ${currentPage === 0 ? 'disabled' : ''}>«</button>
            <button class="pagination-btn" onclick="goToPage(currentPage - 1)" ${currentPage === 0 ? 'disabled' : ''}>‹</button>
            <select class="pagination-select" onchange="goToPage(parseInt(this.value))" style="padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--bg2);color:var(--text);cursor:pointer;">
              ${pageSelectOptions}
            </select>
            <button class="pagination-btn" onclick="goToPage(currentPage + 1)" ${currentPage === pageCount - 1 ? 'disabled' : ''}>›</button>
            <button class="pagination-btn" onclick="goToPage(pageCount - 1)" ${currentPage === pageCount - 1 ? 'disabled' : ''}>»</button>
          </div>
          <select class="pagination-select" onchange="changeItemsPerPage(parseInt(this.value))" style="padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--bg2);color:var(--text);cursor:pointer;">
            ${itemsPerPageOptions}
          </select>
        </div>`;
    }

    wrapper.innerHTML = tableHTML + paginationHTML;
  }

  function changeItemsPerPage(newLimit) {
    itemsPerPage = newLimit;
    currentPage = 0;
    renderTable(filteredAssets);
  }

  function goToPage(pageNum) {
    const pageCount = Math.ceil(filteredAssets.length / itemsPerPage);
    if (pageNum < 0) pageNum = 0;
    if (pageNum >= pageCount) pageNum = pageCount - 1;
    currentPage = pageNum;
    renderTable(filteredAssets);
    // Scroll table into view
    document.getElementById('tableWrapper').scrollIntoView({ behavior: 'smooth' });
  }

  function toggleSelectAll(checkbox) {
    const pageCount = Math.ceil(filteredAssets.length / itemsPerPage);
    const start = currentPage * itemsPerPage;
    const end = Math.min(start + itemsPerPage, filteredAssets.length);
    const pageAssets = filteredAssets.slice(start, end);

    if (checkbox.checked) {
      pageAssets.forEach(a => {
        selectedAssets.add(a.uid || '');
      });
    } else {
      pageAssets.forEach(a => {
        selectedAssets.delete(a.uid || '');
      });
    }
    updateSelectedBadge();
    renderTable(filteredAssets);
  }

  function toggleSelectRow(checkbox) {
    const uid = checkbox.dataset.uid;
    if (checkbox.checked) {
      selectedAssets.add(uid);
    } else {
      selectedAssets.delete(uid);
    }
    updateSelectedBadge();
  }

  function updateSelectedBadge() {
    const badge = document.getElementById('selectedBadge');
    const btnSeeDetails = document.getElementById('btnSeeDetails');
    const count = selectedAssets.size;

    if (count > 0) {
      badge.textContent = `${count} selected`;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }

    if (btnSeeDetails) {
      btnSeeDetails.disabled = count !== 1;
      btnSeeDetails.title = count === 1 ? "Show details for selected asset" : "Select exactly 1 asset to see details";
    }
  }

  function showSelectedAssetDetails() {
    if (selectedAssets.size !== 1) return;
    const uid = Array.from(selectedAssets)[0];
    showAssetDetailsModal(uid);
  }

  let currentDetailUid = null;

  /**
   * ASSET DETAILS MODAL — with lazy loading of details (CI7)
   */
  async function showAssetDetailsModal(uid) {
    const asset = allAssets.find(a => a.uid === uid);
    if (!asset) return;
    currentDetailUid = uid;

    // Show modal immediately with basic info
    document.getElementById('detTitle').textContent = asset.title || 'Untitled';
    document.getElementById('detContent').style.display = 'block';
    document.getElementById('detLoading').style.display = 'none';

    // Image
    const detImg = document.getElementById('detImage');
    if (asset.thumbnail_url || asset.image_urls?.length) {
      detImg.src = `/api/image/${uid}`;
      detImg.dataset.uid = uid;
      detImg.style.display = 'block';
    } else {
      detImg.style.display = 'none';
      detImg.dataset.uid = '';
    }

    // Basic info (always available from listing)
    _renderDetailSeller(asset);
    document.getElementById('detType').innerHTML = asset.listing_type ? `<a href="javascript:void(0)" style="color:inherit;text-decoration:underline dashed;" onclick="setFilterByClick('type-cb', '${escapeHtml(asset.listing_type)}'); closeAssetDetailsModal();">${escapeHtml(asset.listing_type)}</a>` : '—';
    document.getElementById('detFormats').innerHTML = renderTagList(asset.asset_formats, 'format-cb');
    document.getElementById('detUe').innerHTML = renderTagList(asset.engine_versions, 'engine-cb');
    document.getElementById('detLicenses').innerHTML = renderTagList(asset.licenses, 'license-cb');
    document.getElementById('detPrice').textContent = formatPrice(asset) || '—';
    document.getElementById('detRating').textContent = asset.average_rating ? `${Number(asset.average_rating).toFixed(1)} / 5` : '—';
    document.getElementById('detAdded').textContent = asset.created_at ? asset.created_at.substring(0, 10) : '—';
    document.getElementById('detUpdated').textContent = asset.last_updated_at ? asset.last_updated_at.substring(0, 10) : '—';
    document.getElementById('detTags').innerHTML = renderTagList(asset.tags);
    document.getElementById('detDesc').textContent = asset.description || 'No description provided.';
    const localCommentInput = document.getElementById('detLocalComment');
    if (localCommentInput) {
      localCommentInput.value = getAssetUserData(uid).comment;
    }
    updateDetailFavoriteUi(uid);
    updateDetailCommentStatus(uid);

    // Hide detail-only sections initially
    document.getElementById('detTechSpecsSection').style.display = 'none';
    document.getElementById('detMediaSection').style.display = 'none';

    const fabLink = document.getElementById('detFabLink');
    if (asset.fab_url) {
      fabLink.href = asset.fab_url;
      fabLink.style.display = 'inline-block';
    } else {
      fabLink.style.display = 'none';
    }

    document.getElementById('assetDetailsModal').style.display = 'flex';

    // Lazy load details if missing, or if the cache was marked detailed but lacks enriched fields
    const needsDetailsFetch = !asset.details_fetched || !hasEnrichedDetails(asset);
    if (needsDetailsFetch) {
      document.getElementById('detLoading').style.display = 'block';
      document.getElementById('detContent').style.opacity = '0.5';

      try {
        const resp = await fetch(`/api/details/${uid}`);
        if (resp.ok) {
          const enriched = await resp.json();
          // Update the asset in allAssets
          const idx = allAssets.findIndex(a => a.uid === uid);
          if (idx !== -1) {
            Object.assign(allAssets[idx], enriched);
            _renderEnrichedDetails(allAssets[idx]);
          }
        }
      } catch(e) {
        console.error('Error fetching details:', e);
      } finally {
        document.getElementById('detLoading').style.display = 'none';
        document.getElementById('detContent').style.opacity = '1';
      }
    } else {
      // Details already fetched — render enriched info
      _renderEnrichedDetails(asset);
    }
  }

  function _renderDetailSeller(asset) {
    const sellerEl = document.getElementById('detSeller');
    const avatarEl = document.getElementById('detSellerAvatar');

    sellerEl.innerHTML = asset.seller_name
      ? `<a href="javascript:void(0)" style="color:inherit;text-decoration:underline dashed;" onclick="setFilterByClick('seller-cb', '${escapeHtml(asset.seller_name)}'); closeAssetDetailsModal();">${escapeHtml(asset.seller_name)}</a>`
      : '—';

    // Seller avatar (from details)
    const avatarUrl = asset.seller_avatar_url || '';
    if (avatarUrl) {
      avatarEl.src = avatarUrl;
      avatarEl.style.display = 'inline-block';
    } else {
      avatarEl.style.display = 'none';
    }
  }

  function _renderEnrichedDetails(asset) {
    // Update seller with avatar if available
    _renderDetailSeller(asset);

    // Update description (may be richer after details fetch)
    if (asset.description && asset.description !== 'No description provided.') {
      document.getElementById('detDesc').innerHTML = sanitizeHtml(asset.description);
    }

    // Technical specs (from details)
    const techSpecs = asset.technical_specs || '';
    if (techSpecs) {
      document.getElementById('detTechSpecsSection').style.display = 'block';
      document.getElementById('detTechSpecs').innerHTML = sanitizeHtml(techSpecs);
    }

    // Media gallery (from details — listing.medias)
    const mediaUrls = asset.media_urls || [];
    if (mediaUrls.length > 0) {
      document.getElementById('detMediaSection').style.display = 'block';
      const container = document.getElementById('detMedia');
      container.innerHTML = mediaUrls.map((url, i) =>
        `<img src="${escapeHtml(url)}" style="width:100px; height:56px; object-fit:cover; border-radius:4px; cursor:pointer; background:var(--bg3);" onclick="showImageModalFromGallery(${i})" onerror="this.style.display='none'" data-gallery-idx="${i}">`
      ).join('');
    }

    // Update rating with review count if available
    if (asset.average_rating) {
      const reviewCount = asset.review_count || '';
      const ratingText = `${Number(asset.average_rating).toFixed(1)} / 5` + (reviewCount ? ` (${reviewCount} reviews)` : '');
      document.getElementById('detRating').textContent = ratingText;
    }
  }

  function showImageModalFromGallery(idx) {
    const asset = allAssets.find(a => a.uid === currentDetailUid);
    if (!asset || !asset.media_urls?.length) return;

    currentImageModalUrls = asset.media_urls;
    currentImageModalIndex = idx;
    updateImageModalView();

    const modal = document.getElementById('imageModal');
    modal.style.display = 'flex';
  }

  function closeAssetDetailsModal(event) {
    if (event && event.target.id !== 'assetDetailsModal') return;
    currentDetailUid = null;
    document.getElementById('assetDetailsModal').style.display = 'none';
  }

  // ─────────────────────────────────────────────────────────────────────────
  // IMAGE PREVIEW MODAL - Fullscreen Image Viewer
  // ─────────────────────────────────────────────────────────────────────────

  let currentImageModalUrls = [];
  let currentImageModalIndex = 0;

  /**
   * Display fullscreen image modal for preview.
   * Called when user clicks on a preview thumbnail in the table.
   *
   * @param {string} uid - The asset unique identifier
   */
  async function showImageModal(uid) {
    const asset = allAssets.find(a => a.uid === uid);
    if (!asset) return;

    currentImageModalUrls = [];
    currentImageModalIndex = 0;

    // Fetch details if not already done, so we have access to full media gallery
    const needsDetailsFetch = !asset.details_fetched || !hasEnrichedDetails(asset);
    if (needsDetailsFetch) {
      document.body.style.cursor = 'wait'; // Feedback during fetch
      try {
        const resp = await fetch(`/api/details/${uid}`);
        if (resp.ok) {
          const enriched = await resp.json();
          const idx = allAssets.findIndex(a => a.uid === uid);
          if (idx !== -1) {
            Object.assign(allAssets[idx], enriched);
          }
        }
      } catch(e) {
        console.error('Error fetching details for image modal:', e);
      } finally {
        document.body.style.cursor = '';
      }
    }

    // Prefer full media gallery if available
    if (asset.media_urls && asset.media_urls.length > 0) {
      currentImageModalUrls = asset.media_urls;
    } else if (asset.image_urls && asset.image_urls.length > 0) {
      currentImageModalUrls = asset.image_urls;
    } else {
      currentImageModalUrls = [`/api/image/${uid}`];
    }

    updateImageModalView();

    const modal = document.getElementById('imageModal');
    modal.style.display = 'flex';
  }

  function updateImageModalView() {
    if (currentImageModalUrls.length === 0) return;

    const modalImg = document.getElementById('modalImage');
    const countLabel = document.getElementById('modalImageCount');
    const prevBtn = document.getElementById('modalPrevBtn');
    const nextBtn = document.getElementById('modalNextBtn');

    modalImg.src = currentImageModalUrls[currentImageModalIndex];
    countLabel.textContent = `${currentImageModalIndex + 1}/${currentImageModalUrls.length}`;

    if (currentImageModalUrls.length > 1) {
      prevBtn.style.visibility = 'visible';
      nextBtn.style.visibility = 'visible';
    } else {
      prevBtn.style.visibility = 'hidden';
      nextBtn.style.visibility = 'hidden';
    }
  }

  function prevImageModal() {
    if (currentImageModalUrls.length <= 1) return;
    currentImageModalIndex--;
    if (currentImageModalIndex < 0) currentImageModalIndex = currentImageModalUrls.length - 1;
    updateImageModalView();
  }

  function nextImageModal() {
    if (currentImageModalUrls.length <= 1) return;
    currentImageModalIndex++;
    if (currentImageModalIndex >= currentImageModalUrls.length) currentImageModalIndex = 0;
    updateImageModalView();
  }

  /**
   * Close fullscreen image modal.
   * Safely handles multiple close triggers:
   * - Click outside modal: passes click event (prevented by bubbling check)
   * - Escape key: passes keydown event (ignored, closeImageModal() called directly)
   * - X button click: no event (event = null)
   *
   * @param {Event} event - Optional click event from modal-overlay onclick
   *                       null/undefined if called from Escape listener or button
   *
   * Safety check: Only close if click was on modal background (not content)
   * This prevents accidental close when clicking modal image
   */
  function closeImageModal(event) {
    // If event provided, verify it's a click on modal background (id='imageModal')
    // Clicking inside modal content (e.g., the image) will have different target
    if (event && event.target.id !== 'imageModal') return;
    const modal = document.getElementById('imageModal');
    modal.style.display = 'none';
  }

  /**
   * Keyboard listener: Close modals on Escape key press, navigate with arrows.
   */
  document.addEventListener('keydown', (e) => {
    const imgModal = document.getElementById('imageModal');
    const detModal = document.getElementById('assetDetailsModal');

    if (e.key === 'Escape') {
      if (imgModal.style.display !== 'none') closeImageModal();
      else if (detModal.style.display !== 'none') closeAssetDetailsModal();
    }

    if (imgModal.style.display !== 'none') {
      if (e.key === 'ArrowLeft') prevImageModal();
      else if (e.key === 'ArrowRight') nextImageModal();
    }
  });

  function sortBy(col) {
    const sel = document.getElementById('sortSelect');
    if (col === 'title') {
      sel.value = sel.value === 'title_desc' ? 'title_asc' : 'title_desc';
    } else if (col === 'created_at') {
      sel.value = sel.value === 'date_desc' ? 'date_asc' : 'date_desc';
    } else if (col === 'last_updated_at') {
      sel.value = 'updated_desc';
    } else if (col === 'seller_name') {
      sel.value = sel.value === 'seller_desc' ? 'seller_asc' : 'seller_desc';
    } else if (col === 'listing_type') {
      sel.value = sel.value === 'type_desc' ? 'type_asc' : 'type_desc';
    } else if (col === 'asset_formats') {
      sel.value = sel.value === 'format_desc' ? 'format_asc' : 'format_desc';
    }
    applyFilters();
  }

  // Keyboard shortcut: Ctrl+A to select all on current page
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'a' && document.getElementById('searchInput') !== document.activeElement) {
      e.preventDefault();
      const checkbox = document.getElementById('selectAllCheckbox');
      if (checkbox) {
        checkbox.checked = !checkbox.checked;
        toggleSelectAll(checkbox);
      }
    }
  });

  // ─── Export ───────────────────────────────────────────────
  /**
   * Export selected or filtered assets as CSV or JSON.
   *
   * Selection semantics:
   * - If assets are CHECKED: export only selected assets
   * - If NO assets checked: export ALL filtered assets (respects active filters)
   * - Empty selection + no filters = all 3480+ assets
   *
   * Backend behavior (/api/export/csv and /api/export/json):
   * 1. If selected_uids array provided: return only those assets
   * 2. If empty array: return all assets currently in cache
   * 3. Each asset flattened to include: uid, title, ue_max, licenses,
   *    created_at, etc. (see Asset.to_dict() in Python)
   *
   * File naming:
   * - Format: fab_export_YYYY-MM-DD.csv|json
   * - Example: fab_export_2025-03-15.csv
   *
   * Error handling:
   * - Network error: show error message
   * - HTTP error (500): show server response
   * - Uses Set<string> (selectedAssets) for deduplication
   *
   * @param {string} format - Export format: 'csv' or 'json'
   * @async
   */
  async function exportAssets(format) {
    const endpoint = format === 'csv' ? '/api/export/csv' : '/api/export/json';
    // Convert selected UIDs from Set to Array for JSON payload
    // Empty array means "export all" in backend
    const uids = Array.from(selectedAssets);
    const payload = uids.length > 0 ? { selected_uids: uids } : {};

    if (format === 'csv') {
      payload.columns = DISPLAYED_COLS_LIST;
    }

    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        alert('❌ Export error: ' + (await resp.text()));
        return;
      }

      // Download file (browser-native download dialog)
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fab_export_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('❌ Error: ' + e.message);
    }
  }

  async function handleForceRefresh() {
    const response = confirm('🔄 Full refresh will download your entire library without using the cache.\n\nContinue?');
    if (!response) return;

    setProgress(10);
    const debugMode = document.getElementById('debugMode').checked;

    try {
      const resp = await fetch('/api/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cookies: '',
          user_agent: '',
          debug: debugMode,
          refresh_mode: 'full'
        })
      });
      setProgress(80);
      const data = await resp.json();

      if (!resp.ok) {
        alert('❌ Error: ' + (data.error || 'Unknown error'));
        setProgress(0);
        return;
      }

      console.log('✅ Full refresh completed:', data.count);
      await loadAssets();
      setProgress(100);
      setTimeout(() => setProgress(0), 500);
    } catch (e) {
      alert('❌ Network error: ' + e.message);
      setProgress(0);
    }
  }

  // ─── Progress bar ─────────────────────────────────────────
  function setProgress(pct) {
    const bar = document.getElementById('progress');
    bar.style.width = pct + '%';
    if (pct === 0) bar.style.width = '0';
  }

  // ─── Logging Config ───────────────────────────────────────
  async function updateLoggingConfig() {
    const level = document.getElementById('logLevelSelect').value;
    const output = document.getElementById('logOutputSelect').value;
    const debugMode = document.getElementById('debugMode').checked;
    saveLogSettings(level, output, debugMode);
    saveDebugMode(debugMode);
    try {
      await fetch('/api/config/logging', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level, output, debug: debugMode })
      });
    } catch (e) {
      console.error('Failed to update logging config', e);
    }
  }

  // ─── Start ────────────────────────────────────────────────
  init();
// Custom Export Logic
let exportTemplates = {};

async function openExportModal() {
  const exportModal = document.getElementById('exportModal');
  const exportSelect = document.getElementById('exportProfileSelect');
  const exportDescription = document.getElementById('exportProfileDescription');
  if (!exportModal || !exportSelect || !exportDescription) {
    console.error('[FabAssetsManager] Custom export modal is missing required DOM nodes');
    return;
  }

  exportModal.style.display = 'flex';
  exportModal.classList.add('open');
  try {
    const res = await fetch('/api/export-templates');
    if (res.ok) {
      exportTemplates = await res.json();
      exportSelect.innerHTML = '';
      for (const [name, profile] of Object.entries(exportTemplates)) {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        exportSelect.appendChild(option);
      }
      exportSelect.onchange = (e) => {
        const profile = exportTemplates[e.target.value];
        exportDescription.textContent = profile ? profile.description : '';
      };
      if (exportSelect.options.length > 0) exportSelect.dispatchEvent(new Event('change'));
    } else {
      console.error('[FabAssetsManager] Failed to fetch export templates', res.status);
    }
  } catch (e) {
    console.error('Failed to load export templates', e);
  }
}

function resolveCustomExportExtension(profileName, pattern) {
  const name = String(profileName || '').toLowerCase();
  const fmt = String(pattern || '').toLowerCase();
  const looksCsv =
    name.includes('csv') ||
    (fmt.includes(',') && !fmt.includes('|') && !fmt.includes(']('));
  const looksMarkdown =
    name.includes('markdown') ||
    fmt.includes('| %') ||
    fmt.includes('- [%') ||
    fmt.includes('](%');
  if (looksCsv) return 'csv';
  return looksMarkdown ? 'md' : 'txt';
}

function closeExportModal(e) {
  if (e && e.target !== e.currentTarget) return;
  const exportModal = document.getElementById('exportModal');
  if (!exportModal) return;
  exportModal.classList.remove('open');
  exportModal.style.display = 'none';
}

function performCustomExport() {
  console.info('[FabAssetsManager] Custom export requested');
  const profileName = document.getElementById('exportProfileSelect').value;
  if (!profileName || !exportTemplates[profileName]) {
    console.warn('[FabAssetsManager] Custom export aborted: no export profile selected');
    return;
  }
  const profile = exportTemplates[profileName];
  const extension = resolveCustomExportExtension(profileName, profile.pattern);

  const targetAssets = selectedAssets.size > 0
    ? filteredAssets.filter(a => selectedAssets.has(a.uid))
    : filteredAssets;

  let output = [];
  targetAssets.forEach(asset => {
    let line = profile.pattern;
    line = line.replace(/%uid%/g, asset.uid || '');
    line = line.replace(/%title%/g, asset.title || '');
    line = line.replace(/%seller_name%/g, asset.seller_name || '');
    line = line.replace(/%listing_type%/g, asset.listing_type || '');
    line = line.replace(/%ue_max%/g, asset.ue_max || '');
    line = line.replace(/%engine_versions%/g, asset.engine_versions || '');
    line = line.replace(/%licenses%/g, asset.licenses || '');
    line = line.replace(/%fab_url%/g, asset.fab_url || '');
    line = line.replace(/%price%/g, asset.price || '');
    line = line.replace(/%tags%/g, asset.tags || '');
    output.push(line);
  });

  const blob = new Blob([output.join('\n')], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `Fab_export.${extension}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  closeExportModal();
}
