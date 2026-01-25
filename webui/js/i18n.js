/**
 * Korev Evidence — Internationalization (i18n) System
 * 
 * Supports: English (en), French (fr)
 * Default: Auto-detect from browser
 * Persistence: localStorage
 */

const I18N_STORAGE_KEY = 'korev.language';
const SUPPORTED_LANGUAGES = ['en', 'fr'];
const DEFAULT_LANGUAGE = 'en';

// Translation data cache
let translations = {
    en: null,
    fr: null
};

// Current language
let currentLanguage = DEFAULT_LANGUAGE;

/**
 * Detect browser language and map to supported language
 */
function detectBrowserLanguage() {
    const browserLang = navigator.language || navigator.userLanguage || DEFAULT_LANGUAGE;
    const langCode = browserLang.split('-')[0].toLowerCase();
    return SUPPORTED_LANGUAGES.includes(langCode) ? langCode : DEFAULT_LANGUAGE;
}

/**
 * Get stored language preference
 */
function getStoredLanguage() {
    const stored = localStorage.getItem(I18N_STORAGE_KEY);
    if (stored === 'auto') return 'auto';
    if (stored && SUPPORTED_LANGUAGES.includes(stored)) return stored;
    return 'auto';
}

/**
 * Set language preference
 */
function setStoredLanguage(lang) {
    localStorage.setItem(I18N_STORAGE_KEY, lang);
}

/**
 * Get effective language (resolves 'auto')
 */
function getEffectiveLanguage() {
    const stored = getStoredLanguage();
    if (stored === 'auto') {
        return detectBrowserLanguage();
    }
    return stored;
}

/**
 * Load translation file
 */
async function loadTranslations(lang) {
    if (translations[lang]) return translations[lang];
    
    try {
        const response = await fetch(`/i18n/${lang}.json`);
        if (!response.ok) throw new Error(`Failed to load ${lang}.json`);
        translations[lang] = await response.json();
        return translations[lang];
    } catch (error) {
        console.error(`[i18n] Failed to load translations for ${lang}:`, error);
        // Fallback to English
        if (lang !== DEFAULT_LANGUAGE) {
            return loadTranslations(DEFAULT_LANGUAGE);
        }
        return {};
    }
}

/**
 * Get nested value from object by dot-notation path
 */
function getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
        return current && current[key] !== undefined ? current[key] : null;
    }, obj);
}

/**
 * Translate a key with optional parameters
 * @param {string} key - Dot-notation key (e.g., 'common.save', 'chat.tokens_used')
 * @param {object} params - Optional parameters for interpolation
 * @returns {string} Translated string or key if not found
 */
function t(key, params = {}) {
    const langData = translations[currentLanguage] || translations[DEFAULT_LANGUAGE] || {};
    let value = getNestedValue(langData, key);
    
    // Fallback to English if not found in current language
    if (value === null && currentLanguage !== DEFAULT_LANGUAGE) {
        const fallbackData = translations[DEFAULT_LANGUAGE] || {};
        value = getNestedValue(fallbackData, key);
    }
    
    // Return key if not found
    if (value === null) {
        console.warn(`[i18n] Missing translation: ${key}`);
        return key;
    }
    
    // Interpolate parameters: {param} -> value
    if (typeof value === 'string' && Object.keys(params).length > 0) {
        Object.keys(params).forEach(param => {
            value = value.replace(new RegExp(`\\{${param}\\}`, 'g'), params[param]);
        });
    }
    
    return value;
}

/**
 * Initialize i18n system
 */
async function initI18n() {
    currentLanguage = getEffectiveLanguage();
    
    // Load current language and English fallback
    await Promise.all([
        loadTranslations(currentLanguage),
        loadTranslations(DEFAULT_LANGUAGE)
    ]);
    
    console.log(`[i18n] Initialized with language: ${currentLanguage}`);
    return currentLanguage;
}

/**
 * Change language
 * @param {string} lang - Language code ('auto', 'en', 'fr')
 * @returns {Promise<string>} New effective language
 */
async function setLanguage(lang) {
    setStoredLanguage(lang);
    const effectiveLang = lang === 'auto' ? detectBrowserLanguage() : lang;
    
    if (effectiveLang !== currentLanguage) {
        currentLanguage = effectiveLang;
        await loadTranslations(currentLanguage);
    }
    
    // Dispatch event for components to react
    window.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: currentLanguage, setting: lang }
    }));
    
    console.log(`[i18n] Language changed to: ${currentLanguage} (setting: ${lang})`);
    return currentLanguage;
}

/**
 * Get current language info
 */
function getLanguageInfo() {
    return {
        current: currentLanguage,
        setting: getStoredLanguage(),
        supported: SUPPORTED_LANGUAGES,
        isAuto: getStoredLanguage() === 'auto'
    };
}

// ═══════════════════════════════════════════════════════════════════════════
// Alpine.js Store Integration
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Create Alpine.js store for i18n
 */
function createI18nStore() {
    return {
        language: 'auto',
        effectiveLanguage: DEFAULT_LANGUAGE,
        
        async init() {
            await initI18n();
            this.language = getStoredLanguage();
            this.effectiveLanguage = currentLanguage;
            
            // Listen for language changes
            window.addEventListener('languageChanged', (e) => {
                this.effectiveLanguage = e.detail.language;
                this.language = e.detail.setting;
            });
        },
        
        async setLanguage(lang) {
            await setLanguage(lang);
            this.language = lang;
            this.effectiveLanguage = getEffectiveLanguage();
        },
        
        t(key, params = {}) {
            return t(key, params);
        }
    };
}

// ═══════════════════════════════════════════════════════════════════════════
// Global exports
// ═══════════════════════════════════════════════════════════════════════════

// Make t() globally available
window.t = t;
window.i18n = {
    t,
    init: initI18n,
    setLanguage,
    getLanguageInfo,
    createStore: createI18nStore
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    await initI18n();
});
