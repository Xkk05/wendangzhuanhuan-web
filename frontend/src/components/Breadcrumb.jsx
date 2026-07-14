import './Breadcrumb.css';

function Breadcrumb({ items, onNavigate }) {
  return (
    <nav className="breadcrumb">
      {items.map((item, index) => (
        <span key={index} className="breadcrumb-item">
          {index < items.length - 1 ? (
            <>
              <button 
                className="breadcrumb-link"
                onClick={() => onNavigate(item.path)}
              >
                {item.label}
              </button>
              <span className="breadcrumb-separator">{'>'}</span>
            </>
          ) : (
            <span className="breadcrumb-current">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

export default Breadcrumb;
