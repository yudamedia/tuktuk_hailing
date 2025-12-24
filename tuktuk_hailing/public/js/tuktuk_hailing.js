// Tuktuk Hailing Main JS

// Global utilities for the hailing system

window.tuktuk_hailing = {
    /**
     * Format currency in KSH
     */
    format_currency: function(amount) {
        return `KSH ${parseFloat(amount).toLocaleString('en-KE', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        })}`;
    },
    
    /**
     * Format distance
     */
    format_distance: function(km) {
        if (km < 1) {
            return `${Math.round(km * 1000)} m`;
        }
        return `${km.toFixed(2)} km`;
    },
    
    /**
     * Format duration
     */
    format_duration: function(minutes) {
        if (minutes < 60) {
            return `${Math.round(minutes)} min`;
        }
        const hours = Math.floor(minutes / 60);
        const mins = Math.round(minutes % 60);
        return `${hours}h ${mins}m`;
    },
    
    /**
     * Check if location services are available
     */
    check_geolocation: function() {
        return 'geolocation' in navigator;
    },
    
    /**
     * Get current position
     */
    get_current_position: function() {
        return new Promise((resolve, reject) => {
            if (!this.check_geolocation()) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                position => resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                }),
                error => reject(error),
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0
                }
            );
        });
    },
    
    /**
     * Calculate distance between two points (Haversine formula)
     */
    calculate_distance: function(lat1, lng1, lat2, lng2) {
        const R = 6371; // Earth radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                 Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                 Math.sin(dLng/2) * Math.sin(dLng/2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    },
    
    /**
     * Open WhatsApp chat
     */
    open_whatsapp: function(phone_number, message) {
        const encoded_message = encodeURIComponent(message || '');
        const url = `https://wa.me/${phone_number}${message ? '?text=' + encoded_message : ''}`;
        window.open(url, '_blank');
    },
    
    /**
     * Show location permission dialog
     */
    request_location_permission: function() {
        return this.get_current_position();
    }
};

// Load Leaflet CSS if not already loaded
if (typeof L === 'undefined') {
    const leaflet_css = document.createElement('link');
    leaflet_css.rel = 'stylesheet';
    leaflet_css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(leaflet_css);
    
    const leaflet_js = document.createElement('script');
    leaflet_js.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    document.head.appendChild(leaflet_js);
}

console.log('Tuktuk Hailing loaded');
