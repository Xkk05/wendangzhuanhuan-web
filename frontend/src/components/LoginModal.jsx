import React from 'react';
import { useTranslation } from 'react-i18next';
import { Modal, Button, Avatar, Typography, message } from 'antd';
import { UserOutlined, LoadingOutlined, LogoutOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useUserStore } from '../stores/useUserStore';
import '../styles/LoginModal.css';

const { Text, Title, Paragraph } = Typography;

const LoginModal = () => {
    const { t } = useTranslation();
    const {
        userInfo,
        isLoggedIn,
        isPolling,
        isLoginModalVisible,
        hideLoginModal,
        startLoginProcess,
        stopLoginProcess,
        logout
    } = useUserStore();

    // Handle Modal Close
    const handleClose = () => {
        hideLoginModal();
    };

    const handleLogin = () => {
        startLoginProcess();
    };

    const handleCancelLogin = () => {
        stopLoginProcess();
        message.info(t('loginModal.login_cancelled'));
    };

    const handleLogout = () => {
        logout();
    };

    // Render Content based on state
    const renderContent = () => {
        if (isLoggedIn && userInfo) {
            return (
                <div className="login-modal-content">
                    <div className="login-modal-avatar-container">
                        <Avatar size={80} src={userInfo.avatar} icon={<UserOutlined />} />
                        <div className="avatar-badge">
                            <SafetyCertificateOutlined />
                        </div>
                    </div>
                    <Title level={4} className="login-modal-title">{userInfo.nickname}</Title>
                    <Text className="login-modal-subtitle">{t('loginModal.logged_in_as')}</Text>

                    <div className="login-modal-buttons">
                        <Button
                            danger
                            block
                            size="large"
                            className="login-modal-btn-secondary"
                            icon={<LogoutOutlined />}
                            onClick={handleLogout}
                        >
                            {t('loginModal.logout')}
                        </Button>
                        <Button
                            type="text"
                            block
                            className="login-modal-btn-text"
                            onClick={handleClose}
                        >
                            {t('loginModal.close')}
                        </Button>
                    </div>
                </div>
            );
        }

        if (isPolling) {
            return (
                <div className="login-modal-content">
                    <div className="login-polling-container">
                        <LoadingOutlined className="login-polling-icon" spin />
                        <div className="login-polling-title">{t('loginModal.waiting_login')}</div>
                        <div className="login-polling-desc">{t('loginModal.browser_notice')}</div>
                    </div>

                    <div className="login-modal-buttons">
                        <Button
                            size="large"
                            block
                            className="login-modal-btn-secondary"
                            onClick={handleCancelLogin}
                        >
                            {t('loginModal.cancel_login')}
                        </Button>
                    </div>
                </div>
            );
        }

        // Guest State
        return (
            <div className="login-modal-content">
                <div className="login-modal-avatar-container">
                    <Avatar size={80} icon={<UserOutlined />} />
                </div>
                <Title level={4} className="login-modal-title">{t('loginModal.guest_title')}</Title>
                <Paragraph className="login-modal-subtitle">
                    {t('loginModal.guest_subtitle').split('<br />').map((line, i) => (
                        <React.Fragment key={i}>
                            {line}
                            {i === 0 && <br />}
                        </React.Fragment>
                    ))}
                </Paragraph>

                <div className="login-modal-buttons">
                    <Button
                        type="primary"
                        size="large"
                        block
                        className="login-modal-btn-primary"
                        onClick={handleLogin}
                        icon={<UserOutlined />}
                    >
                        {t('loginModal.login_now')}
                    </Button>
                    <Button
                        type="text"
                        size="small"
                        block
                        className="login-modal-btn-text"
                        onClick={handleClose}
                    >
                        {t('loginModal.later')}
                    </Button>
                </div>
            </div>
        );
    };

    return (
        <Modal
            open={isLoginModalVisible}
            onCancel={handleClose}
            footer={null}
            width={340}
            centered
            maskClosable={true}
            destroyOnHidden={true}
            closable={false} // Clean look
            className="custom-login-modal"
            rootClassName="custom-login-modal-root"
            getContainer={() => document.querySelector('.app-container') || document.body}
            styles={{
                mask: { backdropFilter: 'blur(4px)', backgroundColor: 'rgba(0,0,0,0.4)', borderRadius: 'var(--main-radius)' },
                content: { borderRadius: 'var(--main-radius)', padding: '12px', backgroundColor: 'var(--card-bg)' }
            }}
        >
            {renderContent()}
        </Modal>
    );
};

export default LoginModal;
