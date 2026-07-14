import React from 'react';
import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { motion as Motion } from 'framer-motion';

const LoadingPage = ({ message = '正在处理登录请求...', description = '请稍候，我们正在为您跳转回原页面' }) => {
  const antIcon = <LoadingOutlined style={{ fontSize: 48, color: '#2563eb' }} spin />;

  return (
    <div 
      className="fixed inset-0 flex items-center justify-center bg-slate-50 dark:bg-slate-900 z-50"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(248, 250, 252, 0.9)',
        zIndex: 9999
      }}
    >
      <Motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center p-8 bg-white dark:bg-slate-800 rounded-2xl shadow-xl max-w-sm w-full mx-4 border border-slate-100 dark:border-slate-700"
        style={{
          textAlign: 'center',
          padding: '2rem',
          backgroundColor: '#ffffff',
          borderRadius: '1rem',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          maxWidth: '24rem',
          width: '90%',
          border: '1px solid #f1f5f9'
        }}
      >
        <div className="mb-6 relative">
          <Motion.div
            animate={{ 
              scale: [1, 1.1, 1],
              opacity: [0.5, 1, 0.5]
            }}
            transition={{ 
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="absolute inset-0 bg-blue-500/10 rounded-full blur-xl"
          />
          <Spin indicator={antIcon} />
        </div>
        
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          {message}
        </h2>
        
        <p className="text-slate-500 dark:text-slate-400 text-sm">
          {description}
        </p>

        <div className="mt-8 flex justify-center gap-1">
          {[0, 1, 2].map((i) => (
            <Motion.div
              key={i}
              animate={{ 
                scale: [1, 1.5, 1],
                opacity: [0.3, 1, 0.3]
              }}
              transition={{ 
                duration: 1,
                repeat: Infinity,
                delay: i * 0.2
              }}
              className="w-1.5 h-1.5 bg-blue-500 rounded-full"
            />
          ))}
        </div>
      </Motion.div>
    </div>
  );
};

export default LoadingPage;
