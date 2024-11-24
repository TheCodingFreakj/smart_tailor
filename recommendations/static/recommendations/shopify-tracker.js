(function() {
    console.log("Tracking script loaded!");

    function getShopFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get("shop");
      }

    // Get the shop parameter
    const shop = getShopFromUrl();
    console.log("Shop parameter:", shop);  

           // Track some activity, e.g., product view, cart addition, etc.
    function trackCustomerActivity(activityData) {
        // Your backend endpoint where you want to send the data
        const backendUrl = 'https://smart-tailor.onrender.com/track-activity/'; // Adjust the URL as needed

        fetch(backendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: {"activityData": JSON.stringify(activityData), "shop":shop},
        })
        .then(response => response.json())
        .then(data => {
            console.log("Activity tracked:", data);
        })
        .catch(error => {
            console.error("Error tracking activity:", error);
        });
    }

     // Example: Track page view
     const trackPageView = () => {
        const eventData = {
            customerId: window.customerInfo?.id || null,
            event: 'page_view',
            url: window.location.href,
            timestamp: new Date().toISOString(),
            action: "track_activity"
        };
        trackCustomerActivity(eventData);
    };


    const getAddToCartButtons = () => {
        const buttons = [];
        
        // Look for buttons or links that typically trigger add-to-cart actions
        const byButtonType = document.querySelectorAll('button[type="submit"], button[type="button"], input[type="submit"], a[href*="cart"], a[href*="add-to-cart"]');
        buttons.push(...byButtonType);
    
        // You can also check for clickable elements with a role="button" or any other common properties
        const byRoleButton = document.querySelectorAll('[role="button"]');
        buttons.push(...byRoleButton);
        
        return buttons;
    };
    

    const trackAddToCart = (productId) => {
        const eventData = {
            customerId: window.customerInfo?.id || null,
            event: 'add_to_cart',
            product_id: productId,
            timestamp: new Date().toISOString(),
            action: "track_activity"
        };
        trackCustomerActivity(eventData);
    };

    // Listen for add-to-cart events dynamically
    const addToCartButtons = getAddToCartButtons();
    addToCartButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const productId = event.target.dataset.productId || event.target.closest('[data-product-id]').dataset.productId;
            trackAddToCart(productId);
        });
    });

    trackPageView();
    // });
})();
