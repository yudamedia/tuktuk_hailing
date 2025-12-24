// Copyright (c) 2024, Sunny Tuktuk and contributors
// Driver hailing dashboard functionality

frappe.ui.form.on('TukTuk Driver', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            add_hailing_dashboard(frm);
        }
    }
});

function add_hailing_dashboard(frm) {
    // Render hailing dashboard into HTML field on Hailing tab
    const html_field = frm.fields_dict.hailing_dashboard_html;
    if (!html_field || !html_field.$wrapper) return;

    html_field.$wrapper.html(
        frappe.render_template('hailing_dashboard', {driver_id: frm.doc.name})
    );

    // Initialize map and controls
    setTimeout(() => {
        initHailingMap(frm);
        initHailingControls(frm);
        loadPendingRequests(frm);
    }, 500);
}

function initHailingMap(frm) {
    const mapContainer = document.getElementById('hailing-map');
    if (!mapContainer) return;
    
    // Initialize Leaflet map
    const map = L.map('hailing-map').setView([-4.2833, 39.5667], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    frm.hailing_map = map;
    frm.driver_markers = {};
    frm.my_marker = null;
    
    // Start location tracking if available for hailing is ON
    if (frm.doc.hailing_status === 'Available') {
        startLocationTracking(frm);
    }
}

function initHailingControls(frm) {
    // Available toggle button
    const toggleBtn = document.getElementById('hailing-toggle-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => toggleAvailability(frm));
        updateToggleButton(frm);
    }
}

async function toggleAvailability(frm) {
    const isCurrentlyAvailable = frm.doc.hailing_status === 'Available';
    const newStatus = !isCurrentlyAvailable;
    
    try {
        const result = await frappe.call({
            method: 'tuktuk_hailing.api.location.set_driver_availability',
            args: {
                driver_id: frm.doc.name,
                available: newStatus
            }
        });
        
        if (result.message.success) {
            frm.doc.hailing_status = result.message.status;
            updateToggleButton(frm);
            
            if (newStatus) {
                startLocationTracking(frm);
                frappe.show_alert({message: 'You are now available for hailing!', indicator: 'green'});
            } else {
                stopLocationTracking(frm);
                frappe.show_alert({message: 'You are now offline', indicator: 'orange'});
            }
        }
    } catch (error) {
        frappe.msgprint('Error updating availability');
    }
}

function updateToggleButton(frm) {
    const toggleBtn = document.getElementById('hailing-toggle-btn');
    const statusBadge = document.getElementById('hailing-status-badge');
    
    if (!toggleBtn) return;
    
    const isAvailable = frm.doc.hailing_status === 'Available';
    
    toggleBtn.textContent = isAvailable ? 'Go Offline' : 'Go Available';
    toggleBtn.className = 'btn ' + (isAvailable ? 'btn-warning' : 'btn-success');
    
    if (statusBadge) {
        statusBadge.textContent = frm.doc.hailing_status || 'Offline';
        statusBadge.className = 'badge badge-' + (isAvailable ? 'success' : 'secondary');
    }
}

function startLocationTracking(frm) {
    if (frm.location_interval) return; // Already tracking
    
    if (!navigator.geolocation) {
        frappe.msgprint('Geolocation not supported on this device');
        return;
    }
    
    // Update location immediately
    updateLocation(frm);
    
    // Then update every 10 seconds (configurable from settings)
    frm.location_interval = setInterval(() => {
        updateLocation(frm);
    }, 10000);
}

function stopLocationTracking(frm) {
    if (frm.location_interval) {
        clearInterval(frm.location_interval);
        frm.location_interval = null;
    }
}

function updateLocation(frm) {
    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const accuracy = position.coords.accuracy;
            const heading = position.coords.heading;
            const speed = position.coords.speed;
            
            try {
                await frappe.call({
                    method: 'tuktuk_hailing.api.location.update_driver_location',
                    args: {
                        driver_id: frm.doc.name,
                        latitude: lat,
                        longitude: lng,
                        accuracy: accuracy,
                        heading: heading,
                        speed: speed ? speed * 3.6 : null, // Convert m/s to km/h
                        hailing_status: frm.doc.hailing_status
                    }
                });
                
                // Update marker on map
                if (frm.my_marker) {
                    frm.my_marker.setLatLng([lat, lng]);
                } else {
                    frm.my_marker = L.marker([lat, lng], {
                        icon: L.icon({
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41]
                        })
                    }).addTo(frm.hailing_map).bindPopup('You').openPopup();
                    
                    frm.hailing_map.setView([lat, lng], 15);
                }
                
                // Load nearby drivers
                loadNearbyDrivers(frm);
                
            } catch (error) {
                console.error('Location update error:', error);
            }
        },
        (error) => {
            console.error('Geolocation error:', error);
        },
        {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        }
    );
}

async function loadNearbyDrivers(frm) {
    if (!frm.my_marker) return;
    
    const myPos = frm.my_marker.getLatLng();
    
    try {
        const result = await frappe.call({
            method: 'tuktuk_hailing.api.location.get_available_drivers',
            args: {
                customer_lat: myPos.lat,
                customer_lng: myPos.lng,
                max_distance_km: 10
            }
        });
        
        if (result.message) {
            // Clear existing driver markers (except self)
            Object.keys(frm.driver_markers).forEach(driver_id => {
                if (driver_id !== frm.doc.name) {
                    frm.hailing_map.removeLayer(frm.driver_markers[driver_id]);
                }
            });
            
            // Add markers for other drivers
            result.message.forEach(driver => {
                if (driver.driver !== frm.doc.name) {
                    const marker = L.marker(
                        [driver.display_latitude, driver.display_longitude],
                        {
                            icon: L.icon({
                                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                                iconSize: [25, 41],
                                iconAnchor: [12, 41]
                            })
                        }
                    ).addTo(frm.hailing_map).bindPopup(driver.driver_name);
                    
                    frm.driver_markers[driver.driver] = marker;
                }
            });
        }
    } catch (error) {
        console.error('Error loading nearby drivers:', error);
    }
}

async function loadPendingRequests(frm) {
    const requestsContainer = document.getElementById('pending-requests');
    if (!requestsContainer) return;
    
    try {
        const result = await frappe.call({
            method: 'tuktuk_hailing.api.rides.get_pending_requests_for_driver',
            args: {
                driver_id: frm.doc.name
            }
        });
        
        if (result.message && result.message.length > 0) {
            requestsContainer.innerHTML = result.message.map(req => `
                <div class="ride-request-card" data-request-id="${req.name}">
                    <div class="request-header">
                        <strong>${req.pickup_address.substring(0, 50)}</strong>
                        <span class="badge badge-info">${req.distance_to_pickup_km} km away</span>
                    </div>
                    <div class="request-body">
                        <p><strong>To:</strong> ${req.destination_address.substring(0, 50)}</p>
                        <p><strong>Fare:</strong> KSH ${req.estimated_fare}</p>
                    </div>
                    <div class="request-actions">
                        <button class="btn btn-success btn-sm" onclick="acceptRideRequest('${req.name}')">
                            Accept Ride
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            requestsContainer.innerHTML = '<p class="text-muted">No pending ride requests</p>';
        }
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

async function acceptRideRequest(request_id) {
    try {
        const result = await frappe.call({
            method: 'tuktuk_hailing.api.rides.accept_ride_request_by_driver',
            args: {
                request_id: request_id,
                driver_id: cur_frm.doc.name
            }
        });
        
        if (result.message.success) {
            frappe.show_alert({message: 'Ride accepted!', indicator: 'green'});
            showActiveRide(result.message);
        } else {
            frappe.msgprint(result.message.error || 'Could not accept ride');
        }
    } catch (error) {
        frappe.msgprint('Error accepting ride');
    }
}

function showActiveRide(rideData) {
    const activeRideContainer = document.getElementById('active-ride');
    const pendingRequestsContainer = document.getElementById('pending-requests');
    
    if (pendingRequestsContainer) {
        pendingRequestsContainer.innerHTML = '';
    }
    
    if (activeRideContainer) {
        activeRideContainer.innerHTML = `
            <div class="active-ride-card">
                <h4>Active Ride</h4>
                <p><strong>Customer:</strong> ${rideData.customer_name || rideData.customer_phone}</p>
                <p><strong>Pickup:</strong> ${rideData.pickup_address}</p>
                <p><strong>Destination:</strong> ${rideData.destination_address}</p>
                <p><strong>Fare:</strong> KSH ${rideData.estimated_fare}</p>
                <button class="btn btn-primary" onclick="openCustomerWhatsApp('${rideData.customer_phone}')">
                    💬 Contact Customer
                </button>
                <button class="btn btn-success" onclick="completeRide()">
                    ✅ Complete Ride
                </button>
            </div>
        `;
    }
}

function openCustomerWhatsApp(phone) {
    const message = encodeURIComponent('Hello! I\'m your Sunny Tuktuk driver. I\'m on my way!');
    window.open(`https://wa.me/${phone}?text=${message}`, '_blank');
}

async function completeRide() {
    const fareInput = await frappe.prompt({
        label: 'Actual Fare Charged',
        fieldname: 'actual_fare',
        fieldtype: 'Currency',
        reqd: 1
    });
    
    if (fareInput && fareInput.actual_fare) {
        // Call complete ride API
        frappe.msgprint('Ride completion functionality will be implemented');
    }
}

// Template for hailing dashboard
frappe.templates['hailing_dashboard'] = `
<div class="hailing-dashboard">
    <div class="row">
        <div class="col-md-8">
            <div id="hailing-map" style="height: 400px; border-radius: 8px;"></div>
        </div>
        <div class="col-md-4">
            <div class="hailing-controls">
                <div class="form-group">
                    <label>Status: <span id="hailing-status-badge" class="badge">Offline</span></label>
                    <button id="hailing-toggle-btn" class="btn btn-success btn-block">
                        Go Available
                    </button>
                </div>
                
                <div id="active-ride"></div>
                
                <div class="pending-requests-section">
                    <h5>Pending Requests</h5>
                    <div id="pending-requests"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
    .hailing-dashboard {
        padding: 15px;
        background: #f8f9fa;
        border-radius: 8px;
        margin-top: 15px;
    }
    
    .hailing-controls {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .ride-request-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
    }
    
    .request-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .request-actions {
        margin-top: 10px;
    }
    
    .active-ride-card {
        background: #d1ecf1;
        border: 2px solid #0c5460;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
`;
