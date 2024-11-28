(function () {
    const shopUrl = "https://smart-tailor.onrender.com";  // Your backend URL
    const currentProductId = ShopifyAnalytics.meta.product.id;

    fetch(`${shopUrl}/recommendations-widget/?product_id=${currentProductId}`)
        .then((response) => response.json())
        .then((data) => {
            if (data.recommendations && data.recommendations.length > 0) {
                const recommendations = data.recommendations;
                let widgetHtml = `<div id="recommendation-widget"><h3>Recommended for You</h3><ul>`;
                recommendations.forEach((product) => {
                    widgetHtml += `
                        <li>
                            <a href="${product.url}">
                                <img src="${product.image}" alt="${product.title}">
                                <p>${product.title}</p>
                                <p>$${product.price}</p>
                            </a>
                        </li>`;
                });
                widgetHtml += `</ul></div>`;
                document.querySelector(".product-form").insertAdjacentHTML("afterend", widgetHtml);
            }
        })
        .catch((error) => console.error("Error loading recommendations:", error));
})();
