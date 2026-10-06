let priceChart = null;
let movementChart = null;


// ============================================================
// FORMATO DE DINERO
// ============================================================

function money(value) {

    if (
        value === null ||
        value === undefined ||
        Number.isNaN(Number(value))
    ) {
        return "---";
    }

    return "$" + Number(value).toLocaleString(
        "en-US",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    );
}


// ============================================================
// FORMATO DE NÚMEROS
// ============================================================

function integer(value) {

    if (
        value === null ||
        value === undefined ||
        Number.isNaN(Number(value))
    ) {
        return "---";
    }

    return Number(value).toLocaleString(
        "en-US"
    );
}


// ============================================================
// FECHA UTC
// ============================================================

function fechaCorta(value) {

    if (!value) {
        return "---";
    }

    const fecha = new Date(value);

    if (Number.isNaN(fecha.getTime())) {
        return String(value);
    }

    return fecha.toLocaleString(
        "es-PA",
        {
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "UTC"
        }
    ) + " UTC";
}


// ============================================================
// PETICIONES
// ============================================================

async function obtener(url) {

    const respuesta = await fetch(url);

    const datos = await respuesta.json();

    if (!respuesta.ok) {

        throw new Error(
            datos.mensaje ||
            "Error al consultar " + url
        );
    }

    return datos;
}


// ============================================================
// RESUMEN
// ============================================================

async function cargarResumen() {

    try {

        const data =
            await obtener("/api/resumen");


        document.getElementById(
            "precioAnalisis"
        ).textContent =
            money(data.precio_ultimo);


        document.getElementById(
            "maximo"
        ).textContent =
            money(data.precio_maximo);


        document.getElementById(
            "minimo"
        ).textContent =
            money(data.precio_minimo);


        document.getElementById(
            "registros"
        ).textContent =
            integer(data.registros);


        document.getElementById(
            "tickVolume"
        ).textContent =
            integer(data.tick_volume_total);


        document.getElementById(
            "periodo"
        ).textContent =
            `${fechaCorta(data.fecha_inicio)} → ${fechaCorta(data.fecha_fin)}`;

    }

    catch (error) {

        console.error(
            "Resumen:",
            error
        );

        document.getElementById(
            "periodo"
        ).textContent =
            "No se pudieron cargar los datos";
    }
}


// ============================================================
// METATRADER 5
// ============================================================

async function cargarPrecioMT5() {

    const dot =
        document.getElementById(
            "mt5Dot"
        );

    const status =
        document.getElementById(
            "mt5Status"
        );

    const system =
        document.getElementById(
            "mt5System"
        );


    try {

        const data =
            await obtener(
                "/api/precio"
            );


        document.getElementById(
            "bid"
        ).textContent =
            money(data.bid);


        document.getElementById(
            "ask"
        ).textContent =
            money(data.ask);


        document.getElementById(
            "spread"
        ).textContent =
            money(data.spread);


        dot.className =
            "dot online";


        status.textContent =
            "MT5 conectado";


        system.textContent =
            "CONECTADO";


        system.style.color =
            "#25d0a6";

    }

    catch (error) {

        console.error(
            "MT5:",
            error
        );


        document.getElementById(
            "bid"
        ).textContent =
            "---";


        document.getElementById(
            "ask"
        ).textContent =
            "---";


        document.getElementById(
            "spread"
        ).textContent =
            "---";


        dot.className =
            "dot offline";


        status.textContent =
            "MT5 no disponible";


        system.textContent =
            "NO DISPONIBLE";


        system.style.color =
            "#ff6178";
    }
}


// ============================================================
// GRÁFICA DE PRECIO
// ============================================================

async function cargarGraficaPrecio() {

    try {

        const data =
            await obtener(
                "/api/precios"
            );


        const labels =
            data.datos.map(
                x => fechaCorta(x.fecha)
            );


        const valores =
            data.datos.map(
                x => Number(x.precio)
            );


        const ctx =
            document.getElementById(
                "priceChart"
            );


        if (priceChart) {
            priceChart.destroy();
        }


        priceChart =
            new Chart(
                ctx,
                {

                    type: "line",

                    data: {

                        labels: labels,

                        datasets: [

                            {

                                label:
                                    "ETH/USD",

                                data:
                                    valores,

                                borderColor:
                                    "#8f7cff",

                                backgroundColor:
                                    "rgba(143,124,255,.12)",

                                fill: true,

                                tension: .28,

                                pointRadius: 0,

                                borderWidth: 2

                            }

                        ]
                    },


                    options: {

                        responsive: true,

                        maintainAspectRatio: false,

                        interaction: {

                            intersect: false,

                            mode: "index"
                        },


                        plugins: {

                            legend: {

                                labels: {

                                    color:
                                        "#9caec4"
                                }
                            }
                        },


                        scales: {

                            x: {

                                ticks: {

                                    color:
                                        "#65778f",

                                    maxTicksLimit:
                                        9
                                },

                                grid: {

                                    color:
                                        "rgba(255,255,255,.04)"
                                }
                            },


                            y: {

                                ticks: {

                                    color:
                                        "#65778f",

                                    callback:
                                        value =>
                                            "$" +
                                            Number(value)
                                                .toLocaleString()
                                },

                                grid: {

                                    color:
                                        "rgba(255,255,255,.05)"
                                }
                            }
                        }
                    }
                }
            );

    }

    catch (error) {

        console.error(
            "Gráfica:",
            error
        );
    }
}


// ============================================================
// MOVIMIENTOS
// ============================================================

async function cargarMovimientos() {

    try {

        const data =
            await obtener(
                "/api/movimientos"
            );


        const contenedor =
            document.getElementById(
                "movimientosTable"
            );


        if (!data.datos.length) {

            contenedor.textContent =
                "No hay movimientos registrados.";

            return;
        }


        const filas =
            data.datos.slice(
                0,
                10
            );


        const columnas =
            Object.keys(
                filas[0]
            );


        let html =
            "<table><thead><tr>";


        columnas
            .slice(0, 4)
            .forEach(
                col => {

                    html +=
                        `<th>${col}</th>`;
                }
            );


        html +=
            "</tr></thead><tbody>";


        filas.forEach(
            fila => {

                html +=
                    "<tr>";


                columnas
                    .slice(0, 4)
                    .forEach(
                        col => {

                            let valor =
                                fila[col];


                            if (
                                String(col)
                                    .toLowerCase()
                                    .includes("fecha")
                            ) {

                                valor =
                                    fechaCorta(
                                        valor
                                    );
                            }


                            else if (
                                typeof valor ===
                                "number"
                            ) {

                                valor =
                                    valor.toFixed(
                                        4
                                    );
                            }


                            html +=
                                `<td>${valor ?? "---"}</td>`;
                        }
                    );


                html +=
                    "</tr>";
            }
        );


        html +=
            "</tbody></table>";


        contenedor.innerHTML =
            html;

    }

    catch (error) {

        console.error(
            "Movimientos:",
            error
        );

        document.getElementById(
            "movimientosTable"
        ).textContent =
            "No se pudo cargar la tabla.";
    }
}


// ============================================================
// GRÁFICA ALCISTAS / BAJISTAS
// ============================================================

async function cargarMovimientoChart() {

    try {

        const data =
            await obtener(
                "/api/precios"
            );


        let alcistas = 0;

        let bajistas = 0;

        let iguales = 0;


        for (
            let i = 1;
            i < data.datos.length;
            i++
        ) {

            const actual =
                Number(
                    data.datos[i].precio
                );


            const anterior =
                Number(
                    data.datos[i - 1].precio
                );


            if (
                actual > anterior
            ) {

                alcistas++;
            }

            else if (
                actual < anterior
            ) {

                bajistas++;
            }

            else {

                iguales++;
            }
        }


        const ctx =
            document.getElementById(
                "movementChart"
            );


        if (movementChart) {
            movementChart.destroy();
        }


        movementChart =
            new Chart(
                ctx,
                {

                    type: "doughnut",

                    data: {

                        labels: [
                            "Alcistas",
                            "Bajistas",
                            "Sin cambio"
                        ],

                        datasets: [

                            {

                                data: [
                                    alcistas,
                                    bajistas,
                                    iguales
                                ],

                                backgroundColor: [
                                    "#25d0a6",
                                    "#ff6178",
                                    "#63758c"
                                ],

                                borderWidth: 0
                            }
                        ]
                    },


                    options: {

                        responsive: true,

                        maintainAspectRatio: false,

                        plugins: {

                            legend: {

                                position:
                                    "bottom",

                                labels: {

                                    color:
                                        "#9caec4",

                                    padding:
                                        16
                                }
                            }
                        }
                    }
                }
            );

    }

    catch (error) {

        console.error(
            "Movimiento:",
            error
        );
    }
}


// ============================================================
// CELERY
// ============================================================

async function cargarCelery() {

    const elemento =
        document.getElementById(
            "celerySystem"
        );


    try {

        const data =
            await obtener(
                "/api/celery"
            );


        if (
            data.conectado
        ) {

            elemento.textContent =
                `ACTIVO · ${data.trabajadores.length} worker(s)`;


            elemento.style.color =
                "#25d0a6";
        }

        else {

            elemento.textContent =
                "NO DISPONIBLE";

            elemento.style.color =
                "#ff6178";
        }

    }

    catch (error) {

        elemento.textContent =
            "NO DISPONIBLE";

        elemento.style.color =
            "#ff6178";
    }
}


// ============================================================
// EXCEL
// ============================================================

async function cargarExcel() {

    const elemento =
        document.getElementById(
            "excelSystem"
        );


    try {

        const data =
            await obtener(
                "/api/hojas"
            );


        elemento.textContent =
            `VERIFICADO · ${data.hojas.length} hojas`;


        elemento.style.color =
            "#25d0a6";

    }

    catch (error) {

        elemento.textContent =
            "NO ENCONTRADO";


        elemento.style.color =
            "#ff6178";
    }
}


// ============================================================
// ACTUALIZAR TODO
// ============================================================

async function actualizarTodo() {

    await Promise.all([

        cargarResumen(),

        cargarPrecioMT5(),

        cargarGraficaPrecio(),

        cargarMovimientos(),

        cargarMovimientoChart(),

        cargarCelery(),

        cargarExcel()

    ]);
}


// ============================================================
// INICIO
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        actualizarTodo();


        // Precio MT5 cada 5 segundos

        setInterval(
            cargarPrecioMT5,
            5000
        );


        // Datos del análisis cada minuto

        setInterval(
            () => {

                cargarResumen();

                cargarGraficaPrecio();

                cargarCelery();

                cargarExcel();

            },
            60000
        );

    }
);
// ============================================================
// 30 ACTIVIDADES DESDE EXCEL
// ============================================================

let actividadesProyecto = [];


// ============================================================
// ESCAPAR HTML
// ============================================================

function escaparHTML(valor) {

    if (
        valor === null ||
        valor === undefined
    ) {

        return "";

    }


    return String(valor)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );
}


// ============================================================
// CARGAR ACTIVIDADES
// ============================================================

async function cargarActividades() {

    const contenedor =
        document.getElementById(
            "actividadesGrid"
        );


    try {

        const data =
            await obtener(
                "/api/actividades"
            );


        if (
            !data.ok ||
            !data.actividades
        ) {

            contenedor.innerHTML = `

                <div class="activity-error">

                    No se pudieron cargar las actividades.

                </div>

            `;

            return;
        }


        actividadesProyecto =
            data.actividades;


        contenedor.innerHTML = "";


        actividadesProyecto.forEach(
            actividad => {

                const numero =
                    String(
                        actividad.numero
                    ).padStart(
                        2,
                        "0"
                    );


                const tarjeta =
                    document.createElement(
                        "button"
                    );


                tarjeta.className =
                    "activity-card";


                tarjeta.type =
                    "button";


                tarjeta.onclick =
                    () => abrirActividad(
                        actividad.numero
                    );


                tarjeta.innerHTML = `

                    <div class="activity-card-top">

                        <span class="activity-number">

                            ${numero}

                        </span>

                        <span class="activity-check">

                            ✓

                        </span>

                    </div>


                    <div class="activity-card-title">

                        ${escaparHTML(
                            actividad.titulo
                        )}

                    </div>


                    <div class="activity-card-bottom">

                        <span>
                            Completada
                        </span>

                        <span class="activity-arrow">
                            →
                        </span>

                    </div>

                `;


                contenedor.appendChild(
                    tarjeta
                );

            }
        );

    }

    catch (error) {

        console.error(
            "Actividades:",
            error
        );


        contenedor.innerHTML = `

            <div class="activity-error">

                Error al leer las actividades
                desde el Excel.

                <br><br>

                ${escaparHTML(
                    error.message
                )}

            </div>

        `;

    }
}


// ============================================================
// ABRIR ACTIVIDAD
// ============================================================

function abrirActividad(numero) {

    const actividad = actividadesProyecto.find(
        item => Number(item.numero) === Number(numero)
    );

    if (!actividad) {
        return;
    }

    document.getElementById("modalNumero").textContent =
        String(actividad.numero).padStart(2, "0");

    document.getElementById("modalTitulo").textContent =
        actividad.titulo || "Actividad";

    document.getElementById("modalResultado").textContent =
        actividad.resultado || "Sin resultado registrado.";

    document.getElementById("modalInterpretacion").textContent =
        actividad.interpretacion ||
        "No existe una interpretación registrada.";

    const contenedorDatos =
        document.getElementById("modalDatos");

    contenedorDatos.innerHTML = "";

    const datos = actividad.datos || {};

    const claves = Object.keys(datos);

    if (claves.length === 0) {

        contenedorDatos.innerHTML =
            '<div class="no-data">No hay datos adicionales registrados.</div>';

    } else {

        const tabla = document.createElement("table");

        tabla.className = "activity-data-table";

        const encabezado = document.createElement("thead");

        encabezado.innerHTML = `
            <tr>
                <th>Campo</th>
                <th>Valor registrado</th>
            </tr>
        `;

        tabla.appendChild(encabezado);

        const cuerpo = document.createElement("tbody");

        claves.forEach(clave => {

            const fila = document.createElement("tr");

            const campo = document.createElement("td");

            campo.textContent = clave;

            const valor = document.createElement("td");

            let contenido = datos[clave];

            if (contenido === null ||
                contenido === undefined ||
                contenido === "") {

                contenido = "—";

            }

            if (Array.isArray(contenido)) {

                contenido = contenido.join(", ");

            }

            valor.textContent = contenido;

            fila.appendChild(campo);

            fila.appendChild(valor);

            cuerpo.appendChild(fila);
        });

        tabla.appendChild(cuerpo);

        contenedorDatos.appendChild(tabla);
    }

    document
        .getElementById("actividadModal")
        .classList.add("show");

    document.body.classList.add("modal-open");
}


// ============================================================
// CERRAR ACTIVIDAD
// ============================================================

function cerrarActividad() {

    document.getElementById(
        "actividadModal"
    ).classList.remove(
        "show"
    );


    document.body.classList.remove(
        "modal-open"
    );
}


// ============================================================
// CERRAR AL HACER CLICK FUERA
// ============================================================

document.addEventListener(
    "click",
    function(event) {

        const modal =
            document.getElementById(
                "actividadModal"
            );


        if (
            event.target === modal
        ) {

            cerrarActividad();

        }

    }
);


// ============================================================
// ESCAPE PARA CERRAR
// ============================================================

document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Escape"
        ) {

            cerrarActividad();

        }

    }
);


// ============================================================
// AGREGAR CARGA DE ACTIVIDADES AL INICIO
// ============================================================

const cargarActividadesOriginal =
    window.actualizarTodo;


window.actualizarTodo =
    async function() {

        if (
            typeof cargarActividadesOriginal ===
            "function"
        ) {

            await cargarActividadesOriginal();

        }


        await cargarActividades();

    };
    // ============================================================
// GALERÍA DE GRÁFICAS
// ============================================================

async function cargarGaleria() {

    const contenedor = document.getElementById("galeria-grid");
    const contador = document.getElementById("total-graficas");

    if (!contenedor) {
        return;
    }

    try {

        const respuesta = await fetch("/api/galeria");
        const datos = await respuesta.json();

        if (!datos.ok) {
            contenedor.innerHTML = `
                <div class="gallery-empty">
                    <div class="empty-icon">⚠</div>
                    <h3>No se pudo cargar la galería</h3>
                    <p>${datos.error || "Error desconocido"}</p>
                </div>
            `;
            return;
        }

        contador.textContent = datos.total;

        if (!datos.imagenes || datos.imagenes.length === 0) {

            contenedor.innerHTML = `
                <div class="gallery-empty">
                    <div class="empty-icon">▧</div>
                    <h3>No hay gráficas disponibles</h3>
                    <p>
                        Todavía no se encontraron imágenes en
                        resultados/graficas.
                    </p>
                </div>
            `;

            return;
        }

        contenedor.innerHTML = "";

        datos.imagenes.forEach((imagen, indice) => {

            const tarjeta = document.createElement("div");

            tarjeta.className = "gallery-card";

            tarjeta.innerHTML = `
                <div class="gallery-image-container">

                    <img
                        src="${imagen.url}"
                        alt="${imagen.titulo}"
                        class="gallery-image"
                        loading="lazy"
                    >

                    <div class="gallery-overlay">
                        <button
                            class="gallery-view-button"
                            onclick="abrirGrafica(${indice})"
                        >
                            ⛶ Ver gráfica
                        </button>
                    </div>

                </div>

                <div class="gallery-info">

                    <div class="gallery-activity">
                        ${
                            imagen.actividad
                            ? "ACTIVIDAD " +
                              String(imagen.actividad).padStart(2, "0")
                            : "GRÁFICA"
                        }
                    </div>

                    <h3>${imagen.titulo}</h3>

                    <p>${imagen.archivo}</p>

                </div>
            `;

            contenedor.appendChild(tarjeta);
        });

        window.galeriaImagenes = datos.imagenes;

    } catch (error) {

        console.error("Error cargando galería:", error);

        contenedor.innerHTML = `
            <div class="gallery-empty">
                <div class="empty-icon">⚠</div>
                <h3>Error al cargar las gráficas</h3>
                <p>
                    Comprueba que Flask esté ejecutándose correctamente.
                </p>
            </div>
        `;
    }
}


// ============================================================
// ABRIR GRÁFICA GRANDE
// ============================================================

function abrirGrafica(indice) {

    const imagenes = window.galeriaImagenes || [];

    const imagen = imagenes[indice];

    if (!imagen) {
        return;
    }

    const modal = document.getElementById("grafica-modal");

    if (!modal) {
        return;
    }

    const imagenGrande =
        document.getElementById("grafica-modal-img");

    const titulo =
        document.getElementById("grafica-modal-title");

    const archivo =
        document.getElementById("grafica-modal-file");

    titulo.textContent = imagen.titulo;

    archivo.textContent =
        imagen.archivo;

    imagenGrande.src =
        imagen.url;

    imagenGrande.alt =
        imagen.titulo;

    modal.classList.add("active");

    document.body.classList.add("modal-open");
}


// ============================================================
// CERRAR MODAL DE GRÁFICA
// ============================================================

function cerrarGrafica() {

    const modal =
        document.getElementById("grafica-modal");

    if (!modal) {
        return;
    }

    modal.classList.remove("active");

    document.body.classList.remove("modal-open");
}


// ============================================================
// CERRAR CON ESC
// ============================================================

document.addEventListener("keydown", function(event) {

    if (event.key === "Escape") {
        cerrarGrafica();
    }

});


// ============================================================
// CARGAR GALERÍA AL INICIAR
// ============================================================

document.addEventListener("DOMContentLoaded", function() {

    cargarGaleria();

});