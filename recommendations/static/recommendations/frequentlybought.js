(function() {
    console.log("Tracking script loaded!");
    console.log('Logged In Customer:', window.loggedInCustomer);


  // Function to extract query parameters from the script's URL
  function getScriptQueryParams(scriptName) {
    // Get all script tags
    const scripts = document.getElementsByTagName("script");

    // Find the specific script by name
    for (let script of scripts) {
      if (script.src && script.src.includes(scriptName)) {
        // Extract query parameters from the script's URL
        const urlParams = new URLSearchParams(script.src.split("?")[1]);
        return Object.fromEntries(urlParams.entries());
      }
    }

    // Return empty object if no match found
    return {};
  }
  
  // Get the query parameters for the current script
  const queryParams = getScriptQueryParams("frequentlybought.js");
  console.log(queryParams)
  const shop = queryParams["shop"];

           // Track some activity, e.g., product view, cart addition, etc.
    function trackCustomerActivity(activityData) {
        // Your backend endpoint where you want to send the data
        const backendUrl = 'https://8433-2409-4062-4ec1-c432-cc9c-f253-28fd-d289.ngrok-free.app/track-activity-add-cart/'; // Adjust the URL as needed

        fetch(backendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(activityData),
        })
        .then(response => response.json())
        .then(data => {
            console.log("Activity tracked:", data);
        })
        .catch(error => {
            console.error("Error tracking activity:", error);
        });
    }

    if (window.json_output || window.config_data_json) {
        console.log(window.json_output);  // "Awesome Product"
        console.log(window.config_data_json);         // 99.99
    }

    

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
            customerId: window.loggedInCustomer.id || null,
            event: 'add_to_cart',
            product_id: productId,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            action: "show_related_product_based_on_often_bought",
            shop:shop
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
   
})();
