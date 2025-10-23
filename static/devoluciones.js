const API_URL = 'http://localhost:8000/api';

// Buscar venta
async function buscarVenta() {
    const numeroVenta = document.getElementById('numeroVenta').value.trim();
    
    if (!numeroVenta) {
        mostrarError('Por favor ingrese un número de venta');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/obtener-productos-venta?numero=${numeroVenta}`);
        
        if (!response.ok) {
            throw new Error('Venta no encontrada');
        }

        const data = await response.json();
        mostrarProductos(data);
        document.getElementById('formDevolucion').style.display = 'block';
    } catch (error) {
        mostrarError(error.message);
        document.getElementById('formDevolucion').style.display = 'none';
    }
}

// Mostrar productos
function mostrarProductos(productos) {
    const container = document.getElementById('productosContainer');
    
    if (!productos || productos.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                No se encontraron productos para esta venta
            </div>
        `;
        return;
    }

    let html = '<div class="productos-list">';
    
    productos.forEach((producto, index) => {
        html += `
            <div class="producto-item">
                <div class="form-check">
                    <input class="form-check-input" 
                           type="checkbox" 
                           id="producto${index}"
                           value="${producto.id}"
                           data-precio="${producto.precio}"
                           data-cantidad="${producto.cantidad}">
                    <label class="form-check-label" for="producto${index}">
                        <div class="producto-info">
                            <h6>${producto.nombre}</h6>
                            <div class="producto-detalles">
                                <span class="badge bg-primary">Cant: ${producto.cantidad}</span>
                                <span class="badge bg-success">$${producto.precio}</span>
                                <span class="badge bg-info">Total: $${(producto.precio * producto.cantidad).toFixed(2)}</span>
                            </div>
                        </div>
                    </label>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Mostrar error
function mostrarError(mensaje) {
    const container = document.getElementById('productosContainer');
    container.innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle"></i>
            ${mensaje}
        </div>
    `;
}

// Procesar devolución
document.addEventListener('DOMContentLoaded', function() {
    const formDevolucion = document.getElementById('formDevolucion');
    
    if (formDevolucion) {
        formDevolucion.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const productosSeleccionados = [];
            document.querySelectorAll('#productosContainer input[type="checkbox"]:checked').forEach(checkbox => {
                productosSeleccionados.push({
                    id: checkbox.value,
                    cantidad: checkbox.dataset.cantidad,
                    precio: checkbox.dataset.precio
                });
            });

            if (productosSeleccionados.length === 0) {
                alert('Por favor seleccione al menos un producto');
                return;
            }

            const datosDevolucion = {
                numero_venta: document.getElementById('numeroVenta').value,
                productos: productosSeleccionados,
                motivo: document.getElementById('motivoDevolucion').value,
                devolver_inventario: document.getElementById('devolverInventario').checked,
                observaciones: document.getElementById('observaciones').value
            };

            try {
                const response = await fetch(`${API_URL}/procesar-devolucion`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(datosDevolucion)
                });

                if (!response.ok) {
                    throw new Error('Error al procesar la devolución');
                }

                const resultado = await response.json();
                alert('Devolución procesada exitosamente');
                
                // Limpiar formulario
                formDevolucion.reset();
                document.getElementById('numeroVenta').value = '';
                document.getElementById('productosContainer').innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-check-circle" style="font-size: 3rem; color: #28a745;"></i>
                        <p class="mt-3">Devolución procesada exitosamente</p>
                    </div>
                `;
                formDevolucion.style.display = 'none';
                
            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    }
});