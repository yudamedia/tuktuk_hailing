# Tuktuk Hailing

Ride hailing system for Sunny Tuktuk fleet management.

## Features

- Real-time GPS tracking of available tuktuks
- OpenStreetMap integration for mapping
- Customer ride requests with pickup and destination
- Driver acceptance/rejection of ride requests
- WhatsApp integration for driver-customer communication
- Fare estimation and calculation
- Service area geofencing
- M-Pesa payment integration

## Installation

```bash
cd ~/frappe-bench
bench get-app https://github.com/your-repo/tuktuk_hailing.git
bench --site sunnytuktuk.com install-app tuktuk_hailing
bench --site sunnytuktuk.com migrate
```

## Integration with Tuktuk Management

This app integrates with the `tuktuk_management` app to:
- Link ride payments to driver targets
- Track hailing performance metrics
- Manage driver availability
- Process payments through existing M-Pesa flow

## License

MIT
