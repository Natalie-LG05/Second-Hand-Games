const image_file_field = document.getElementById('image_file');
const price_field = document.getElementById('price');
const description_field = document.getElementById('description');
const name_field = document.getElementById('name');

async function autoFillFields() {
    const imageFile = image_file_field.files[0];

    if (imageFile) {
        const formData = new FormData();
        formData.append('image', imageFile);

        const response = await fetch('/analyze-image', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data) {
            // Generate product name
            let name = '';
            if (data.game_name && data.game_name !== "None") {
                name = data.game_name;
            } else {
                const nameParts = [data.console_brand, data.console_model];
                name = nameParts.filter(part => part && part !== "None").join(' ');
            }
            name_field.value = name;

            // Build product description
            const descParts = [];

            if (data.console_brand && data.console_brand !== "None") {
                descParts.push(data.console_brand);
            }

            if (data.game_name && data.game_name !== "None") {
                descParts.push(`Game: ${data.game_name}`);
            } else if (data.console_model && data.console_model !== "None") {
                descParts.push(`Console: ${data.console_model}`);
            }

            if (data.controller_type && data.controller_type !== "None") {
                descParts.push(`Controller: ${data.controller_type}`);
            }

            description_field.value = descParts.join(' | ');

            // Fill price if valid
            if (data.estimated_price && data.estimated_price !== "None") {
                price_field.value = data.estimated_price;
            }

            // Optional debug output
            // if (!document.getElementById("ai-debug")) {
            //     const pre = document.createElement("pre");
            //     pre.id = "ai-debug";
            //     pre.style = "background:#f9f9f9; padding:10px; margin-top:10px;";
            //     document.querySelector("form").appendChild(pre);
            // }
            // document.getElementById("ai-debug").textContent = JSON.stringify(data, null, 2);
        }
    }
}

// Trigger on image selection
document.addEventListener("DOMContentLoaded", () => {
    image_file_field.addEventListener("change", autoFillFields);
});