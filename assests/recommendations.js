
  document.addEventListener("DOMContentLoaded", () => {
    
    if (window.json_output || window.config_data_json) {
      console.log(window.json_output);  // "Awesome Product"
      console.log(window.config_data_json);         // 99.99
  }

  // Function to apply styles from configData
function applyStylesFromConfig() {
  const config = window.config_data_json;

  // Set the CSS variables dynamically
  document.documentElement.style.setProperty('--button-text', config.buttonText);
  document.documentElement.style.setProperty('--button-width', config.buttonStyles.width);
  document.documentElement.style.setProperty('--button-height', config.buttonStyles.height);
  document.documentElement.style.setProperty('--button-border-radius', config.buttonStyles.borderRadius);
  document.documentElement.style.setProperty('--button-background-color', config.buttonStyles.backgroundColor);
  document.documentElement.style.setProperty('--button-color', config.buttonStyles.color);
  document.documentElement.style.setProperty('--button-font-size', config.buttonStyles.fontSize);

  document.documentElement.style.setProperty('--slider-width', config.sliderStyles.width);
  document.documentElement.style.setProperty('--slider-height', config.sliderStyles.height);
  document.documentElement.style.setProperty('--slider-background-color', config.sliderStyles.backgroundColor);
  document.documentElement.style.setProperty('--slider-border-radius', config.sliderStyles.borderRadius);
  document.documentElement.style.setProperty('--slider-display', config.sliderStyles.display);
  document.documentElement.style.setProperty('--slider-z-index', config.sliderStyles.zIndex);

  document.documentElement.style.setProperty('--close-button-background-color', config.closeButtonStyles.backgroundColor);
  document.documentElement.style.setProperty('--close-button-color', config.closeButtonStyles.color);
  document.documentElement.style.setProperty('--close-button-padding', config.closeButtonStyles.padding);
  document.documentElement.style.setProperty('--close-button-font-size', config.closeButtonStyles.fontSize);
  document.documentElement.style.setProperty('--close-button-border-radius', config.closeButtonStyles.borderRadius);

  document.documentElement.style.setProperty('--slide-margin', config.slideStyles.margin);
  document.documentElement.style.setProperty('--slide-background-color', config.slideStyles.backgroundColor);
  document.documentElement.style.setProperty('--slide-padding', config.slideStyles.padding);
  document.documentElement.style.setProperty('--slide-border-radius', config.slideStyles.borderRadius);
  document.documentElement.style.setProperty('--slide-box-shadow', config.slideStyles.boxShadow);
}

// Call this function when the page loads or when configData is updated
applyStylesFromConfig();
    // Select elements
    const openSliderButton = document.getElementById("open-slider-btn");
    const productSlider = document.getElementById("product-slider");
    const closeButton = document.getElementById("close-btn");

    openSliderButton.addEventListener("click", () => {
      productSlider.style.display = "block";
      setTimeout(() => {
        productSlider.style.right = "0";
      }, 50);
    });

    closeButton.addEventListener("click", () => {
      productSlider.style.right = "-30%";  // Hidden off-screen again
      setTimeout(() => {
        productSlider.style.display = "none";
      }, 300);
    });

    // Prevent adding the same content again on reload
    if (!productSlider.hasAttribute('data-loaded')) {
      productSlider.setAttribute('data-loaded', 'true');  // Mark the slider as populated

      if (window.json_output && window.json_output.length > 0) {
        window.json_output.forEach(recommendation => {
          const slide = document.createElement("div");
          slide.classList.add("slide");

          slide.innerHTML = `
            <div class="product">
              <h3>${recommendation.product_name}</h3>
              <p>Product ID: ${recommendation.product_id}</p>
              <p>Recommendation Score: ${recommendation.recommendation_score}</p>
              <p>Timestamp: ${recommendation.timestamp}</p>
              <p>Customer ID: ${recommendation.customer_id}</p>
            </div>
          `;
          productSlider.appendChild(slide);
        });
      }
    }
  });


