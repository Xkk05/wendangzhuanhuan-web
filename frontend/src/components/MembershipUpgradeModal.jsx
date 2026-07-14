import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Modal, Radio, Space, Spin, Typography, App, Tag, Card, Row, Col } from 'antd';
import { AuthService } from '../services/auth';
import { useMembershipStore } from '../stores/useMembershipStore';
import { useUserStore } from '../stores/useUserStore';
import './MembershipUpgradeModal.css';

const { Paragraph, Text, Title } = Typography;

function formatPrice(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return '0.00';
  }
  return num.toFixed(2);
}

function normalizePlans(plans) {
  if (!Array.isArray(plans)) {
    return [];
  }

  return plans
    .map((plan) => ({
      id: plan?.id ?? plan?.package_id ?? plan?.packageId ?? null,
      name: plan?.name || plan?.package_name || '会员套餐',
      description: plan?.description || '',
      benefit_text: plan?.benefit_text || plan?.benefitText || '',
      days: Number(plan?.days ?? plan?.package_days ?? 0) || 0,
      price_yuan: Number(plan?.price_yuan ?? plan?.price ?? 0) || 0,
      cover_url: plan?.cover_url || '',
      tag: plan?.tag || (plan?.days === 30 ? '推荐' : plan?.days === 90 ? '热销' : ''),
    }))
    .filter((plan) => plan.id !== null);
}

function MembershipUpgradeModal() {
  const { message } = App.useApp();
  const {
    isUpgradeModalVisible,
    upgradeMessage,
    paymentUrl,
    openUpgradeModal,
    closeUpgradeModal,
  } = useMembershipStore();
  const { token, userProfile, refreshProfile } = useUserStore();

  const [loading, setLoading] = useState(false);
  const [plans, setPlans] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [payType, setPayType] = useState(1);
  const [orderData, setOrderData] = useState(null);
  const [polling, setPolling] = useState(false);
  const [resolvedPaymentUrl, setResolvedPaymentUrl] = useState('');
  const timerRef = useRef(null);

  useEffect(() => {
    const handler = (event) => {
      openUpgradeModal({
        message: event?.detail?.message || '试用已结束，请充值后继续使用。',
        paymentUrl: event?.detail?.paymentUrl || '',
      });
    };

    window.addEventListener('membership-required', handler);
    return () => window.removeEventListener('membership-required', handler);
  }, [openUpgradeModal]);

  useEffect(() => {
    if (!isUpgradeModalVisible) {
      setPlans([]);
      setSelectedPlanId(null);
      setOrderData(null);
      setPolling(false);
      setResolvedPaymentUrl('');
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    if (!token) return;

    let alive = true;
    setLoading(true);
    AuthService.getWebMemberPackageInfo(token)
      .then((packageInfo) => {
        if (!alive) return;
        const normalizedPlans = normalizePlans(packageInfo?.data?.packages);
        setPlans(normalizedPlans);
        setSelectedPlanId(normalizedPlans[0]?.id || null);
        setResolvedPaymentUrl(paymentUrl || '');
        if (packageInfo?.data?.web_member_active) {
          // closeUpgradeModal();
          // message.success('当前项目会员已生效');
        }
      })
      .catch((error) => {
        if (!alive) return;
        message.error(error?.message || '获取会员套餐失败');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [isUpgradeModalVisible, paymentUrl, message, token]);

  const startPolling = (orderNo) => {
    if (!token || !orderNo) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    let attempts = 0;
    setPolling(true);
    timerRef.current = setInterval(async () => {
      attempts += 1;
      try {
        const result = await AuthService.checkWebMemberOrderPaystatus(token, orderNo);
        if (Number(result?.data?.pay_status) === 1) {
          clearInterval(timerRef.current);
          timerRef.current = null;
          setPolling(false);
          await refreshProfile();
          setOrderData(null);
          closeUpgradeModal();
          message.success('支付成功，会员状态已刷新');
        } else if (attempts >= 60) {
          clearInterval(timerRef.current);
          timerRef.current = null;
          setPolling(false);
          message.info('支付状态还未完成确认，你可以稍后再次打开会员弹窗查看。');
        }
      } catch (error) {
        clearInterval(timerRef.current);
        timerRef.current = null;
        setPolling(false);
        message.error(error?.message || '查询支付状态失败');
      }
    }, 2000);
  };

  const handleCreateOrder = async () => {
    if (!token || !selectedPlanId) return;

    setLoading(true);
    try {
      const response = await AuthService.createWebMemberOrder(token, {
        packageId: selectedPlanId,
        payType,
      });
      const nextOrder = response?.data || null;
      setOrderData(nextOrder);

      if (payType === 2 && nextOrder?.alipaysubmit_html) {
        const win = window.open('', '_blank', 'noopener,noreferrer');
        if (win) {
          win.document.open();
          win.document.write(nextOrder.alipaysubmit_html);
          win.document.close();
        }
      }

      startPolling(nextOrder?.order_no);
    } catch (error) {
      message.error(error?.message || '创建会员订单失败');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenFallback = () => {
    if (resolvedPaymentUrl) {
      window.open(resolvedPaymentUrl, '_blank', 'noopener,noreferrer');
    }
  };

  function formatDisplayDate(val) {
    if (!val) return '--';
    const d = new Date(val);
    if (isNaN(d.getTime())) return val;
    const Y = d.getFullYear();
    const M = String(d.getMonth() + 1).padStart(2, '0');
    const D = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    return `${Y}/${M}/${D} ${h}:${m}`;
  }

  return (
    <Modal
      open={isUpgradeModalVisible}
      onCancel={closeUpgradeModal}
      footer={null}
      centered
      destroyOnHidden
      width={780}
      className="membership-upgrade-modal"
    >
      <div className="modal-header-row">
        <Title level={3} style={{ margin: 0 }}>开通会员</Title>
        {userProfile?.is_vip && <Tag color="success" className="status-tag">会员有效</Tag>}
      </div>
      <Paragraph className="subtitle-text">
        {upgradeMessage || '7天免费试用已到期，请开通会员后继续使用。'}
      </Paragraph>

      <Row gutter={16} className="status-cards-row">
        <Col span={12}>
          <div className="info-card">
            <div className="info-card-label">试用到期时间</div>
            <div className="info-card-value">{formatDisplayDate(userProfile?.trial_expire_time)}</div>
          </div>
        </Col>
        <Col span={12}>
          <div className="info-card">
            <div className="info-card-label">会员到期时间</div>
            <div className="info-card-value">{formatDisplayDate(userProfile?.vip_expire_time)}</div>
          </div>
        </Col>
      </Row>

      {loading && !plans.length ? (
        <div className="loading-container">
          <Spin size="large" />
        </div>
      ) : (
        <div className="plans-container">
          <Row gutter={[16, 16]}>
            {plans.map((plan) => (
              <Col span={8} key={plan.id}>
                <div 
                  className={`plan-card ${selectedPlanId === plan.id ? 'selected' : ''}`}
                  onClick={() => setSelectedPlanId(plan.id)}
                >
                  {plan.tag && <Tag color="blue" className="plan-tag">{plan.tag}</Tag>}
                  <div className="plan-name">{plan.name}</div>
                  <div className="plan-price-row">
                    <span className="price-symbol">¥</span>
                    <span className="price-value">{formatPrice(plan.price_yuan)}</span>
                    <span className="plan-days">{plan.name.includes('永久') ? '永久' : `${plan.days}天`}</span>
                  </div>
                  <div className="plan-benefit">
                    {plan.benefit_text || '试用到期后可继续使用全部功能'}
                  </div>
                </div>
              </Col>
            ))}
          </Row>

          <div className="payment-section">
            <Text strong>支付方式</Text>
            <Radio.Group
              className="payment-radio-group"
              value={payType}
              onChange={(e) => setPayType(e.target.value)}
            >
              <Radio value={1}>
                <span className="pay-method"><i className="pay-icon wechat" />微信支付</span>
              </Radio>
              <Radio value={2}>
                <span className="pay-method"><i className="pay-icon alipay" />支付宝</span>
              </Radio>
            </Radio.Group>
          </div>

          {orderData?.qrcode_img_url && payType === 1 && (
            <div className="qrcode-container">
              <Card className="qrcode-card">
                <img src={orderData.qrcode_img_url} alt="WeChat Pay" />
                <div className="qrcode-hint">请使用微信扫码支付</div>
              </Card>
            </div>
          )}

          {polling && (
            <Alert 
              type="success" 
              showIcon 
              title="订单已创建，正在查询支付状态..." 
              className="polling-alert"
            />
          )}

          <div className="modal-footer-actions">
            <Button size="large" onClick={closeUpgradeModal}>稍后再说</Button>
            {!orderData ? (
              <Button 
                type="primary" 
                size="large" 
                className="pay-submit-btn"
                onClick={handleCreateOrder} 
                disabled={!selectedPlanId || loading}
              >
                立即支付
              </Button>
            ) : (
              resolvedPaymentUrl && <Button size="large" onClick={handleOpenFallback}>打开备用支付页</Button>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}

export default MembershipUpgradeModal;
