import './App.css'
import { Link } from 'react-router-dom'
function App() {
  return (
    <>
      <div className="nav-segundario fixed-top">
        <Link to="/login">
          <i className="bi bi-book"></i> Campus virtual
        </Link>
        <a href="#contacto">
          <i className="bi bi-telephone"></i> Trabaja con Nosotros
        </a>
        <a className="segundario-destacado" href="https://www.eticaultraport.cl/" target="_blank" rel="noopener noreferrer">
          <i className="bi bi-journal-text"></i> Canal denuncias
        </a>
      </div>

      <nav className="navbar navbar-expand-lg bg-nav-ultraport fixed-top nav-margin-top">
        <div className="container-fluid">
          <a className="navbar-brand" href="/">
            <img src="/logo/logo-ultraport-color.svg" alt="Logo Ultraport" />
          </a>
          
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNavAltMarkup" aria-controls="navbarNavAltMarkup" aria-expanded="false" aria-label="Toggle navigation">
            <span className="navbar-toggler-icon"></span>
          </button>
          
          <div className="collapse navbar-collapse" id="navbarNavAltMarkup">
            <div className="navbar-nav ms-auto">
              <Link className="nav-link" aria-current="page" to="/">Ultraport</Link>              <a className="nav-link" href="https://www.ultraport.cl/servicios.html">Servicios</a>
              <a className="nav-link" href="https://www.ultraport.cl/sostenibilidad.html">Sostenibilidad</a>
              <a className="nav-link" href="https://www.ultraport.cl/orgullo-portuario.html">Orgullo Portuario</a>
              <a className="nav-link" href="https://tripulante.cl/ultraport-noticias/">Noticias</a>
            </div>
          </div>
        </div>
      </nav>

      <div className="index-video-contenedor">
        <video src="https://www.ultraport.cl/videos/ultraport-index-banner.mp4" autoPlay loop muted></video>
        <div className="index-video-bg"></div>

        <div className="index-video-contenido">
          <div className="container">
            <div className="row">
              <div className="col-md-12">
                <h1 className="titulo-light font-bebas font-sombra">Operaciones portuarias</h1>
                <h2 className="titulo-destacado mb-5 font-sombra">seguridad, excelencia, integridad y pasión</h2>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="bg-color01 bg-index-ultraport color04 padding-contenedor">
        <div className="container">
          <div className="row mb-5 d-flex justify-content-evenly">
            <div className="col-md-4 d-flex align-items-center mb-3">
              <img className="img-fluid w-100" src="/images/ola01.png" alt="Ola Ultraport" />
            </div>
            <div className="col-md-6">
              <h2>Nuestros Servicios</h2>
              <div className="titulo-linea"></div>
              <h4>Brindamos soluciones integrales en operaciones portuarias para terminales multipropósito, de contenedores y automatizados, manejando diversos tipos de carga con altos estándares de seguridad, tecnología de vanguardia y flexibilidad operacional que se adapta a las necesidades de cada cliente.</h4>
            </div>
          </div>
          <div className="row d-flex justify-content-between">
            <div className="col-md-3">
              <h3 className="color02">Nuestra Visión</h3>
              <div className="titulo-linea"></div>
              <h5>"Ser referente en calidad de servicio en operaciones portuarias de excelencia"</h5>
            </div>
            <div className="col-md-3">
              <h3 className="color02">Nuestra Misión</h3>
              <div className="titulo-linea"></div>
              <h5>"Realizamos operaciones portuarias con excelencia y seguridad, innovando e implementando nuevas tecnologías a través de un equipo de personas altamente calificado y comprometido con nuestros clientes y comunidades"</h5>
            </div>
            <div className="col-md-3">
              <h3 className="color02">Propósito</h3>
              <div className="titulo-linea"></div>
              <h5>Cuidamos a las personas y potenciamos su desarrollo, impulsando el crecimiento de los principales puertos de Chile.</h5>
            </div>
          </div>
        </div>
      </div>

      <div className="container color01 padding-contenedor">
        <div className="row d-flex align-items-center">
          <div className="col-md-6">
            <div className="row">
              <div className="col-md-10">
                <h2 className="titulo-destacado">Seguridad, excelencia, integridad y pasión</h2>
                <h3>Líder en operaciones portuarias de Arica a Punta Arenas</h3>
                <div className="titulo-linea"></div>
                <p>
                  Ultraport, parte del grupo Ultramar, es líder en operaciones portuarias en Chile, con presencia de Arica a Punta Arenas. Desde 1981 movilizamos con excelencia, seguridad y sostenibilidad más del 95% del comercio exterior nacional, siendo un socio estratégico para nuestros clientes y comunidades.
                </p>
                <a className="btn btn-ult-bgoscuro" href="/ultraport">Saber más</a>
              </div>
            </div>
            <div className="row">
              <div className="col-md-12">
                <h2><span className="titulo-destacado">Presencia</span> <span className="titulo-light">Nacional</span></h2>
                <h5><span className="presencia-destacado">+45</span> años de experiencia </h5>
                <h5><span className="presencia-destacado">+23</span> millones de toneladas movilizadas el 2025</h5>
                <h5><span className="presencia-destacado">+27</span> años en manejo de graneles mineros</h5>
                <a className="btn btn-ult-bgclaro" href="/servicios">Saber más</a>
              </div>
            </div>
          </div>
          <div className="col-md-6">
            <img className="img-fluid w-100" src="/images/index-presencia5.png" alt="Mapa Ultraport" />
          </div>
        </div>
      </div>

      <div className="bg-index-noticias padding-contenedor">
        <section className="container p-0">
          <div className="row padding-titulo d-flex align-items-center">
            <div className="col-md-6">
              <h2><span className="titulo-destacado">Noticias</span> <span className="titulo-light">Destacadas</span></h2>
            </div>
            <div className="col-md-6 text-end link-color02">
              <a className="btn-noticias" href="#noticias">Revisa todas las noticias <i className="bi bi-arrow-right-short"></i></a>
            </div>
          </div>

          <iframe
            className="iframe-noticias"
            src="https://tripulante.cl/ultraport-noticias/embed-ultraport-noticias/"
            title="Noticias destacadas de Ultraport"
            loading="lazy"
            scrolling="no"
            referrerPolicy="strict-origin-when-cross-origin">
          </iframe>
        </section>
      </div>
      <div className="container padding-contenedor">
        <div className="row d-flex justify-content-between">
          <div className="col-md-6 mx-auto text-center">
            <h2><span className="titulo-destacado">Nuestros</span> <span className="titulo-light">Clientes</span></h2>
          </div>

          <div className="row d-flex justify-content-center align-items-center clientes mt-5 mb-3">
            <div className="col-4 col-md-2 text-center">
              <a href="#tps" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/01-tps-nuevo.jpg" alt="Cliente TPS" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#melon" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/03-logo-melon.png" alt="Cliente Melon" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#epa" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/04-logo-epa.jpg" alt="Cliente EPA" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#centinela" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/05-centinela.png" alt="Cliente Centinela" />
              </a>
            </div>
          </div>

          <div className="row d-flex justify-content-center align-items-center clientes movil-no">
            <div className="col-4 col-md-2 text-center">
              <a href="#empedes" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/06-empedes.jpg" alt="Cliente Empedes" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#tpa" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/07-tpa.jpg" alt="Cliente TPA" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#puertoangamos" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/08-puertoangamos.jpg" alt="Cliente Puerto Angamos" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#tpc" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/09-tpc.jpg" alt="Cliente TPC" />
              </a>
            </div>
          </div>

          <div className="row d-flex justify-content-center align-items-center clientes mt-3 movil-no">
            <div className="col-4 col-md-2 text-center">
              <a href="#puertomejillones" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/10-puertomejillones.png" alt="Cliente Puerto Mejillones" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#tgn" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/11-tgn.jpg" alt="Cliente TGN" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#transmares" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/12-transmares.jpg" alt="Cliente Transmares" />
              </a>
            </div>
            <div className="col-4 col-md-2 text-center">
              <a href="#teck" target="_blank" rel="noopener noreferrer">
                <img className="img-fluid" src="/clientes/13-logo-teck.png" alt="Cliente Teck" />
              </a>
            </div>
          </div>
        </div>
      </div>

      <footer className="padding-contenedor" id="contacto">
        <div className="container-fluid">
          <div className="row">
            <div className="col-md-11 mx-auto">
              <div className="row d-flex justify-content-between">
                
                <div className="col-12 col-md-3 mb-5">
                  <img src="/logo/logo-ultraport.svg" alt="Logo Ultraport" />
                  <p className="py-3">Nuestro propósito es cuidar a las personas y potenciar su desarrollo, impulsando el crecimiento de los principales puertos de Chile</p>
                  
                  <div className="d-flex justify-content-between align-items-center sociales">
                    <a href="https://x.com/Ultraport_Chile" target="_blank" rel="noopener noreferrer"><i className="bi bi-twitter-x"></i></a>
                    <a href="https://www.facebook.com/ultraportchile/?locale=es_LA" target="_blank" rel="noopener noreferrer"><i className="bi bi-facebook"></i></a>
                    <a href="https://www.instagram.com/ultraport_/?hl=es" target="_blank" rel="noopener noreferrer"><i className="bi bi-instagram"></i></a>
                    <a href="https://www.youtube.com/@UltraportChile" target="_blank" rel="noopener noreferrer"><i className="bi bi-youtube"></i></a>
                    <a href="https://www.linkedin.com/company/ultraport/?originalSubdomain=cl" target="_blank" rel="noopener noreferrer"><i className="bi bi-linkedin"></i></a>
                  </div>

                  <div className="my-5">
                    <p>SERVICIOS MARÍTIMOS Y TRANSPORTES LTDA.</p>
                    <p>Errázuriz 854, Valparaíso</p>
                    <p>Email: <span className="color02"><a href="mailto:contacto@ultraport.cl">contacto@ultraport.cl</a></span></p>
                  </div>
                </div>

                <div className="col-12 col-md-4 footer-links mb-5">
                  <h3 className="color02">Trabaja con Nosotros</h3>
                  <ul>
                    <li>Ultraport Arica <br /><span className="color02"><a href="mailto:reclutamiento.ari@ultraport.cl">reclutamiento.ari@ultraport.cl</a></span></li>
                    <li>Ultraport Angamos y Terminal Graneles del Norte<br /><span className="color02"><a href="mailto:reclutamiento.ang@ultraport.cl">reclutamiento.ang@ultraport.cl</a></span></li>
                    <li>Ultraport Mejillones y Centinela<br /><span className="color02"><a href="mailto:reclutamiento.mej@ultraport.cl">reclutamiento.mej@ultraport.cl</a></span></li>
                    <li>Ultraport Coquimbo<br /><span className="color02"><a href="mailto:reclutamiento.coq@ultraport.cl">reclutamiento.coq@ultraport.cl</a></span></li>
                    <li>Ultraport Valparaíso<br /><span className="color02"><a href="mailto:reclutamiento.vap@ultraport.cl">reclutamiento.vap@ultraport.cl</a></span></li>
                    <li>Ultraport Punta Arenas - Chacabuco<br /><span className="color02"><a href="mailto:reclutamiento.puq@ultraport.cl">reclutamiento.puq@ultraport.cl</a></span></li>
                    <li>Ultraport Administración Nacional<br /><span className="color02"><a href="mailto:seleccion@ultraport.cl">seleccion@ultraport.cl</a></span></li>
                  </ul>
                </div>

                <div className="col-12 col-md-4">
                  <h3 className="color02">Certificación</h3>
                  <div className="row">
                    <div className="col-md-8">
                      <p>La certificación de Great Place to Work® es el reconocimiento en clima y cultura organizacional.</p>
                    </div>
                    <div className="col-md-4">
                      <img className="img-fluid movil-img-certificacion" src="/images/gptw-2024.png" alt="Certificación Great Place to Work" />
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>

        <div className="footer-segundario">
          <div className="container-fluid">
            <div className="row">
              <div className="col-md-11 mx-auto">
                <div className="row">
                  <div className="col-md-6">
                    <h6>Todos los derechos reservados a Ultraport 2026</h6>
                  </div>
                  <div className="col-md-6 text-end">
                    <h6>Website desarrollado por tripulante.cl</h6>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </>
  )
}

export default App