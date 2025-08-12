/**
 * Longopass AI - IdeaSoft API Wrapper
 * Kolaylaştırılmiş JavaScript API client'ı
 * 
 * @version 1.0.0
 * @author Longopass AI Team
 */

class LongopassAPI {
    constructor(config = {}) {
        this.baseURL = config.baseURL || 'https://longopass-ai.onrender.com';
        this.userPlan = config.userPlan || 'free';
        this.userId = config.userId || this.generateUserId();
        this.timeout = config.timeout || 30000; // 30 saniye
        
        // Event callbacks
        this.onQuizComplete = config.onQuizComplete || null;
        this.onLabComplete = config.onLabComplete || null;
        this.onChatMessage = config.onChatMessage || null;
        this.onError = config.onError || null;
        
        // Chat conversation tracking
        this.currentConversationId = null;
    }
    
    /**
     * Rastgele kullanıcı ID oluştur
     */
    generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * HTTP request helper
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                'X-User-Plan': this.userPlan,
                'X-User-ID': this.userId,
                ...options.headers
            },
            ...options
        };
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(url, {
                ...config,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('İstek zaman aşımına uğradı');
            }
            
            if (this.onError) {
                this.onError(error);
            }
            
            throw error;
        }
    }
    
    /**
     * Quiz analizi gönder
     * @param {Object} answers - Quiz cevapları
     * @returns {Promise<Object>} Analiz sonuçları
     */
    async submitQuiz(answers) {
        try {
            const result = await this.request('/ai/quiz', {
                method: 'POST',
                body: JSON.stringify({ answers })
            });
            
            if (this.onQuizComplete) {
                this.onQuizComplete(result);
            }
            
            return result;
        } catch (error) {
            console.error('Quiz analizi hatası:', error);
            throw error;
        }
    }
    
    /**
     * Tek lab test analizi
     * @param {Object} testData - Test verileri {name, value, unit, reference_range}
     * @returns {Promise<Object>} Analiz sonuçları
     */
    async analyzeSingleLab(testData) {
        try {
            const result = await this.request('/ai/lab/single', {
                method: 'POST',
                body: JSON.stringify({ test: testData })
            });
            
            if (this.onLabComplete) {
                this.onLabComplete({ type: 'single', data: result });
            }
            
            return result;
        } catch (error) {
            console.error('Lab test analizi hatası:', error);
            throw error;
        }
    }
    
    /**
     * Çoklu lab test özeti
     * @param {Array} tests - Test dizisi
     * @param {number} totalSessions - Toplam test seansı sayısı
     * @returns {Promise<Object>} Özet sonuçları
     */
    async analyzeMultipleLabs(tests, totalSessions = 1) {
        try {
            const result = await this.request('/ai/lab/summary', {
                method: 'POST',
                body: JSON.stringify({ 
                    tests, 
                    total_test_sessions: totalSessions 
                })
            });
            
            if (this.onLabComplete) {
                this.onLabComplete({ type: 'summary', data: result });
            }
            
            return result;
        } catch (error) {
            console.error('Lab özeti hatası:', error);
            throw error;
        }
    }
    
    /**
     * Chat konuşması başlat
     * @returns {Promise<number>} Konuşma ID'si
     */
    async startChat() {
        if (this.userPlan !== 'premium') {
            throw new Error('Chat özelliği yalnızca premium kullanıcılar için kullanılabilir');
        }
        
        try {
            const result = await this.request('/ai/chat/start', {
                method: 'POST',
                body: JSON.stringify({})
            });
            
            this.currentConversationId = result.conversation_id;
            return this.currentConversationId;
        } catch (error) {
            console.error('Chat başlatma hatası:', error);
            throw error;
        }
    }
    
    /**
     * Chat mesajı gönder
     * @param {string} message - Gönderilecek mesaj
     * @param {number} conversationId - Konuşma ID (opsiyonel)
     * @returns {Promise<Object>} AI yanıtı
     */
    async sendChatMessage(message, conversationId = null) {
        if (this.userPlan !== 'premium') {
            throw new Error('Chat özelliği yalnızca premium kullanıcılar için kullanılabilir');
        }
        
        const convId = conversationId || this.currentConversationId;
        
        if (!convId) {
            throw new Error('Aktif konuşma bulunamadı. Önce startChat() çağırın.');
        }
        
        try {
            const result = await this.request('/ai/chat', {
                method: 'POST',
                body: JSON.stringify({
                    conversation_id: convId,
                    text: message
                })
            });
            
            if (this.onChatMessage) {
                this.onChatMessage({
                    type: 'response',
                    message: result.reply,
                    conversationId: result.conversation_id,
                    model: result.used_model,
                    latency: result.latency_ms
                });
            }
            
            return result;
        } catch (error) {
            console.error('Chat mesajı hatası:', error);
            throw error;
        }
    }
    
    /**
     * Chat geçmişini al
     * @param {number} conversationId - Konuşma ID
     * @returns {Promise<Array>} Mesaj geçmişi
     */
    async getChatHistory(conversationId = null) {
        const convId = conversationId || this.currentConversationId;
        
        if (!convId) {
            throw new Error('Geçmişi almak için konuşma ID gerekli');
        }
        
        try {
            return await this.request(`/ai/chat/${convId}/history`);
        } catch (error) {
            console.error('Chat geçmişi hatası:', error);
            throw error;
        }
    }
    
    /**
     * IdeaSoft ürün arama entegrasyonu
     * @param {string} supplementName - Aranacak supplement ismi
     * @returns {Promise<Array>} Bulunan ürünler
     */
    async findProducts(supplementName) {
        // Bu fonksiyon IdeaSoft'un ürün arama API'si ile entegre edilmeli
        // Şimdilik örnek ürünler döndürüyor
        
        const exampleProducts = {
            'magnezyum': [
                {
                    id: 1,
                    name: 'Premium Magnezyum 400mg',
                    price: 89.90,
                    currency: 'TRY',
                    image: '/uploads/magnesium.jpg',
                    description: 'Yüksek absorpsiyonlu magnezyum bisglisinat',
                    category: 'Vitaminler',
                    stock: 45,
                    url: '/urun/premium-magnezyum-400mg'
                }
            ],
            'd vitamini': [
                {
                    id: 2,
                    name: 'Vitamin D3 5000 IU',
                    price: 69.90,
                    currency: 'TRY',
                    image: '/uploads/vitamin-d3.jpg',
                    description: 'Yüksek potansli D3 vitamini',
                    category: 'Vitaminler',
                    stock: 32,
                    url: '/urun/vitamin-d3-5000-iu'
                }
            ],
            'omega-3': [
                {
                    id: 3,
                    name: 'Omega-3 Fish Oil Premium',
                    price: 129.90,
                    currency: 'TRY',
                    image: '/uploads/omega3.jpg',
                    description: 'Saf balık yağı omega-3 1000mg',
                    category: 'Omega Yağları',
                    stock: 28,
                    url: '/urun/omega-3-fish-oil-premium'
                }
            ]
        };
        
        const normalizedName = supplementName.toLowerCase();
        
        // Örnek arama mantığı
        for (const [key, products] of Object.entries(exampleProducts)) {
            if (normalizedName.includes(key) || key.includes(normalizedName)) {
                return products;
            }
        }
        
        return [];
    }
    
    /**
     * Quiz önerilerini ürünlerle eşleştir
     * @param {Object} quizResults - Quiz analiz sonuçları
     * @returns {Promise<Array>} Önerilen ürünler
     */
    async getProductRecommendations(quizResults) {
        const recommendations = [];
        
        if (quizResults.supplements) {
            for (const supplement of quizResults.supplements) {
                try {
                    const products = await this.findProducts(supplement.name);
                    if (products.length > 0) {
                        recommendations.push({
                            supplement: supplement,
                            products: products,
                            reason: supplement.reason,
                            priority: this.calculateSupplementPriority(supplement)
                        });
                    }
                } catch (error) {
                    console.warn(`Ürün bulunamadı: ${supplement.name}`, error);
                }
            }
        }
        
        // Önceliğe göre sırala
        return recommendations.sort((a, b) => b.priority - a.priority);
    }
    
    /**
     * Supplement önceliği hesapla
     * @param {Object} supplement - Supplement bilgisi
     * @returns {number} Öncelik skoru
     */
    calculateSupplementPriority(supplement) {
        let priority = 1;
        
        // Temel vitaminler yüksek öncelik
        if (supplement.name.toLowerCase().includes('vitamin')) priority += 2;
        if (supplement.name.toLowerCase().includes('magnezyum')) priority += 2;
        if (supplement.name.toLowerCase().includes('omega')) priority += 1;
        
        // Sağlık durumuna göre öncelik
        if (supplement.reason.toLowerCase().includes('eksiklik')) priority += 3;
        if (supplement.reason.toLowerCase().includes('önemli')) priority += 2;
        if (supplement.reason.toLowerCase().includes('gerekli')) priority += 2;
        
        return priority;
    }
    
    /**
     * Health check - API durumu kontrol et
     * @returns {Promise<Object>} API durumu
     */
    async healthCheck() {
        try {
            return await this.request('/health');
        } catch (error) {
            console.error('Health check hatası:', error);
            throw error;
        }
    }
    
    /**
     * Kullanıcı planını güncelle
     * @param {string} newPlan - Yeni plan ('premium' veya 'free')
     */
    updateUserPlan(newPlan) {
        this.userPlan = newPlan;
    }
    
    /**
     * Kullanıcı ID'sini güncelle
     * @param {string} newUserId - Yeni kullanıcı ID'si
     */
    updateUserId(newUserId) {
        this.userId = newUserId;
        this.currentConversationId = null; // Yeni kullanıcı için chat sıfırla
    }
}

/**
 * IdeaSoft entegrasyon helper'ları
 */
const LongopassIntegration = {
    /**
     * IdeaSoft sepete ürün ekleme
     * @param {number} productId - Ürün ID'si
     * @param {number} quantity - Miktar
     * @returns {Promise<boolean>} Başarı durumu
     */
    async addToCart(productId, quantity = 1) {
        try {
            // IdeaSoft'un sepete ekleme endpoint'ini çağır
            const response = await fetch('/api/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Sepet sayısını güncelle
                this.updateCartCount();
                return true;
            }
            
            throw new Error(result.message || 'Sepete ekleme başarısız');
        } catch (error) {
            console.error('Sepete ekleme hatası:', error);
            return false;
        }
    },
    
    /**
     * Sepet sayısını güncelle
     */
    updateCartCount() {
        // IdeaSoft'un sepet sayısı güncelleme mantığı
        const cartCountElement = document.querySelector('.cart-count');
        if (cartCountElement) {
            const currentCount = parseInt(cartCountElement.textContent) || 0;
            cartCountElement.textContent = currentCount + 1;
        }
        
        // Cart icon'u animate et
        const cartIcon = document.querySelector('.cart-icon');
        if (cartIcon) {
            cartIcon.classList.add('cart-animated');
            setTimeout(() => cartIcon.classList.remove('cart-animated'), 500);
        }
    },
    
    /**
     * Ürün kartı HTML oluştur
     * @param {Object} product - Ürün bilgisi
     * @param {string} reason - Öneri sebebi
     * @returns {string} HTML string
     */
    createProductCard(product, reason = '') {
        return `
            <div class="longopass-product-card" data-product-id="${product.id}">
                <div class="product-image">
                    <img src="${product.image}" alt="${product.name}" loading="lazy">
                </div>
                <div class="product-info">
                    <h5 class="product-name">${product.name}</h5>
                    <p class="product-description">${product.description}</p>
                    ${reason ? `<p class="recommendation-reason"><small>💡 ${reason}</small></p>` : ''}
                    <div class="product-price">
                        <span class="price">₺${product.price}</span>
                        <small class="currency">${product.currency}</small>
                    </div>
                    <div class="product-actions">
                        <button class="btn-add-cart" onclick="LongopassIntegration.addToCart(${product.id})">
                            🛒 Sepete Ekle
                        </button>
                        <a href="${product.url}" class="btn-view-product">Ürünü Gör</a>
                    </div>
                    ${product.stock < 10 ? `<div class="low-stock">⚠️ Son ${product.stock} adet!</div>` : ''}
                </div>
            </div>
        `;
    },
    
    /**
     * Önerileri sayfa üzerinde göster
     * @param {Array} recommendations - Ürün önerileri
     * @param {string} containerId - Container ID'si
     */
    displayRecommendations(recommendations, containerId = 'longopass-recommendations') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Container bulunamadı: ${containerId}`);
            return;
        }
        
        let html = '<h3>🎯 Size Özel Ürün Önerileri</h3>';
        html += '<div class="longopass-products-grid">';
        
        recommendations.forEach(rec => {
            rec.products.forEach(product => {
                html += this.createProductCard(product, rec.reason);
            });
        });
        
        html += '</div>';
        container.innerHTML = html;
        container.style.display = 'block';
    }
};

// Global olarak erişilebilir yap
if (typeof window !== 'undefined') {
    window.LongopassAPI = LongopassAPI;
    window.LongopassIntegration = LongopassIntegration;
}

// Node.js için export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { LongopassAPI, LongopassIntegration };
}

/**
 * Kullanım Örneği:
 * 
 * // API client'ı başlat
 * const longopass = new LongopassAPI({
 *     userPlan: 'premium',
 *     userId: 'ideasoft_user_123',
 *     onQuizComplete: (results) => {
 *         console.log('Quiz tamamlandı:', results);
 *         // Ürün önerilerini göster
 *         longopass.getProductRecommendations(results)
 *             .then(recommendations => {
 *                 LongopassIntegration.displayRecommendations(recommendations);
 *             });
 *     },
 *     onError: (error) => {
 *         console.error('API Hatası:', error);
 *         alert('Bir hata oluştu. Lütfen tekrar deneyin.');
 *     }
 * });
 * 
 * // Quiz gönder
 * longopass.submitQuiz({
 *     age: 30,
 *     gender: 'female',
 *     activity_level: 'moderate',
 *     goals: ['energy', 'immunity']
 * });
 * 
 * // Lab test analizi
 * longopass.analyzeSingleLab({
 *     name: 'Vitamin D',
 *     value: '18',
 *     unit: 'ng/mL',
 *     reference_range: '20-50 ng/mL'
 * });
 * 
 * // Chat başlat
 * await longopass.startChat();
 * const response = await longopass.sendChatMessage('D vitamini eksikliği belirtileri nelerdir?');
 */