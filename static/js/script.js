document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const recordButton = document.getElementById('recordButton');
    const recordingStatus = document.getElementById('recordingStatus');
    const transcription = document.getElementById('transcription');
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const productName = document.getElementById('productName');
    const productSpecs = document.getElementById('productSpecs');
    const productColor = document.getElementById('productColor');
    const productSize = document.getElementById('productSize');
    const productPrice = document.getElementById('productPrice');
    const productLink = document.getElementById('productLink');
    const similarityScore = document.getElementById('similarityScore');
    const statusBanner = document.getElementById('statusBanner');

    // Variables
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let isMinimalMode = statusBanner ? true : false; // Check if we have a status banner (minimal mode)

    // Check for full dependencies if in minimal mode
    if (isMinimalMode) {
        fetch('/check_dependencies')
            .then(response => response.json())
            .then(data => {
                let missingDeps = [];
                for (const [dep, installed] of Object.entries(data)) {
                    if (!installed) missingDeps.push(dep);
                }
                
                if (missingDeps.length > 0) {
                    statusBanner.innerHTML = `
                        <p>⚠️ Running in minimal mode. Voice search disabled.</p>
                        <p>Missing dependencies: ${missingDeps.join(', ')}</p>
                        <p>Run <code>python install_requirements.py</code> to install.</p>
                    `;
                    statusBanner.style.display = 'block';
                    
                    // Disable voice recording in minimal mode
                    if (recordButton) {
                        recordButton.disabled = true;
                        recordButton.title = "Voice search requires additional dependencies";
                    }
                } else {
                    statusBanner.innerHTML = `
                        <p>✅ All dependencies installed! Reload the page or restart the full app.</p>
                    `;
                    statusBanner.style.display = 'block';
                }
            });
    }

    // Functions
    function updateProductCard(product, score) {
        productName.textContent = product.name;
        productSpecs.textContent = product.specifications;
        productColor.textContent = product.color;
        productSize.textContent = product.size;
        productPrice.textContent = product.price;
        productLink.href = product.website;
        similarityScore.textContent = score.toFixed(2);
    }

    function clearProductCard() {
        productName.textContent = 'No product found';
        productSpecs.textContent = '-';
        productColor.textContent = '-';
        productSize.textContent = '-';
        productPrice.textContent = '-';
        productLink.href = '#';
        similarityScore.textContent = '-';
    }

    function startRecording() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                isRecording = true;
                recordButton.classList.add('recording');
                recordButton.querySelector('.text').textContent = 'Stop Recording';
                recordingStatus.textContent = 'Recording...';
                
                audioChunks = [];
                mediaRecorder = new MediaRecorder(stream);
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    sendAudioToServer(audioBlob);
                    
                    // Stop all tracks on the stream to stop the microphone
                    stream.getTracks().forEach(track => track.stop());
                });
                
                mediaRecorder.start();
            })
            .catch(error => {
                console.error('Error accessing microphone:', error);
                alert('Could not access microphone. Please check permissions.');
            });
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            recordButton.classList.remove('recording');
            recordButton.querySelector('.text').textContent = 'Start Recording';
            recordingStatus.textContent = 'Processing...';
        }
    }

    function sendAudioToServer(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm'); // Add explicit filename
        
        recordingStatus.textContent = 'Sending to server...';
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Server error: ' + response.status);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Safely update transcription element if it exists
            if (transcription) {
                transcription.textContent = data.transcription || 'No transcription available';
            }
            
            updateProductCard(data.product, data.similarity_score);
            recordingStatus.textContent = 'Done';
        })
        .catch(error => {
            console.error('Error processing audio:', error);
            recordingStatus.textContent = 'Error: ' + error.message;
            
            // Safely update transcription element if it exists
            if (transcription) {
                transcription.textContent = 'Error: Could not process audio. Try text search instead.';
            }
            
            clearProductCard();
        });
    }

    function searchProduct() {
        const query = searchInput.value.trim();
        if (!query) return;
        
        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            updateProductCard(data.product, data.similarity_score);
        })
        .catch(error => {
            console.error('Error searching products:', error);
            alert('Error searching products: ' + error.message);
            clearProductCard();
        });
    }

    // Event listeners
    if (recordButton) {
        recordButton.addEventListener('click', () => {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        });
    }
    
    if (searchButton) {
        searchButton.addEventListener('click', searchProduct);
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchProduct();
            }
        });
    }
});
